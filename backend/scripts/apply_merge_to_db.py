#!/usr/bin/env python3
"""Apply ingredient merges directly to the live DB.

Usage: python backend/scripts/apply_merge_to_db.py
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "retreat_ops.db"

MERGE_GROUPS: dict[str, list[str]] = {
    "Black tea": ["black tea loose leaf", "black tea powder dust", "loose leaf black tea"],
    "Bay leaves": ["Bay leaf", "bay leaves"],
    "Cilantro": ["Cilantro", "Fresh cilantro"],
    "Ginger": ["Ginger", "Fresh ginger", "Ginger paste"],
    "Mint": ["Mint", "fresh mint", "fresh mint leaves", "mint leaves"],
    "Garlic": ["Garlic", "garlic cloves"],
    "Coriander powder": ["Coriander powder", "Ground coriander"],
    "Cardamom powder": ["cardamom powder", "ground cardamom"],
    "Red chili powder": ["Red chili powder", "Red chilly powder"],
    "Ground cumin": ["Ground cumin", "Roasted ground cumin", "Jeera Powder"],
    "Turmeric": ["Turmeric", "Turmeric Powder"],
    "Fenugreek powder": ["fenugreek powder", "roasted fenugreek powder"],
    "Amchur": ["dried raw mango powder", "Dried raw mango powder (amchur)"],
    "Nutmeg": ["nutmeg", "Nutmeg (whole)"],
    "Mustard powder": ["raw mustard powder", "mustard seed powder"],
    "Cardamom": ["Cardamom", "cardamom pods", "whole cardamom pods"],
    "Cumin seeds": ["Cumin seeds", "Jeera"],
    "Cinnamon": ["Cinnamon", "cinnamon stick", "cinnamon sticks"],
    "Cloves": ["Cloves", "whole cloves"],
    "Black pepper": ["Black pepper", "black peppercorns"],
    "Kasuri methi": ["Kasuri methi", "dried fenugreek leaves", "Dried fenugreek leaves (kasuri methi)"],
    "Fenugreek seeds": ["Fenugreek", "Methi seeds"],
    "Panch phoran": ["Panch phoran", "panch phoron"],
    "Ajwain": ["Ajwain", "carom seeds"],
    "Asafoetida (hing)": ["Asafoetida (hing)", "Hing"],
    "Saffron": ["Saffron", "saffron strands"],
    "Besan": ["Besan", "gram flour"],
    "Green chilies": ["Green chilies", "Green chillies", "Thai green chili", "Thai green chilies"],
    "Dried red chilies": ["Dried red chilies", "Red chillies"],
    "Tomatoes": ["Tomato", "Tomatoes", "large tomatoes"],
    "Onion": ["Onion", "yellow onion"],
    "Carrots": ["Carrot", "Carrots"],
    "Potatoes": ["Potato", "Potatoes"],
    "Radish": ["Radish", "Radishes"],
    "Drumstick": ["Drumstick", "drumsticks"],
    "Plantain": ["Plantain", "green plantain", "Green plantains"],
    "Okra": ["okra", "Okra (bhindi)"],
    "Avocado": ["Avocado", "Avocado medium"],
    "Green peas": ["Peas", "green peas", "Frozen green peas", "frozen peas"],
    "Cashews": ["Cashew", "Cashews", "cashew nuts"],
    "Crushed roasted peanuts": ["Coarsely crushed roasted peanuts", "Crushed roasted peanuts"],
    "Dried coconut slices": ["dried coconut slices", "Dry Coconut Slices"],
    "Frozen coconut": ["Frozen coconut", "frozen fine-textured coconut", "frozen shredded coconut"],
    "Sesame oil": ["Sesame (Gingelly) Oil", "sesame oil"],
    "Raisins": ["Raisin", "Raisins"],
    "Green mung dal": ["green moong dal", "Green Mung Dal"],
    "Whole green mung": ["Whole green moong", "Whole Green Mung"],
    "Yellow moong dal": ["yellow moong dal", "Yellow split moong dal"],
    "Masoor dal": ["Masoor dal", "split masoor dal"],
    "Black chana": ["Black chana", "black chana dried"],
    "Tamarind": ["Tamarind", "raw tamarind"],
    "Sona Masoori Rice": ["Rice (Sona Masoori)", "Sona Masoori Rice"],
    "Sooji": ["Sooji", "Cream of Wheat (sooji)"],
    "Rolled oats": ["Organic rolled oats", "Rolled Oats"],
    "Khakhra": ["Khakhra", "Khakra"],
    "Lemon or lime": ["Lemon or lime", "Lemon or lime juice", "Lime or lemon"],
    "Filter coffee": ["filter coffee", "Filter Coffee"],
}

FK_TABLES = [
    ("recipe_ingredients", "ingredient_id"),
    ("shopping_list_items", "ingredient_id"),
    ("inventory_items", "ingredient_id"),
]


def get_id(cur: sqlite3.Cursor, name: str) -> int | None:
    row = cur.execute(
        "SELECT id FROM ingredients WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    return row[0] if row else None


def main() -> None:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        sys.exit(1)

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    cur = db.cursor()

    before = cur.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]
    merged = 0

    cur.execute("BEGIN")

    for canonical, aliases in MERGE_GROUPS.items():
        canonical_id = get_id(cur, canonical)

        # If canonical doesn't exist, rename the first available alias
        if not canonical_id:
            for alias in aliases:
                aid = get_id(cur, alias)
                if aid:
                    cur.execute(
                        "UPDATE ingredients SET name = ? WHERE id = ?",
                        (canonical, aid),
                    )
                    canonical_id = aid
                    break

        if not canonical_id:
            continue

        for alias in aliases:
            if alias.lower() == canonical.lower():
                continue
            alias_id = get_id(cur, alias)
            if not alias_id:
                continue

            # Move all FK references to canonical
            for table, col in FK_TABLES:
                cur.execute(
                    f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                    (canonical_id, alias_id),
                )

            # Delete the duplicate
            cur.execute("DELETE FROM ingredients WHERE id = ?", (alias_id,))
            merged += 1

    db.commit()

    after = cur.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]
    ri = cur.execute("SELECT COUNT(*) FROM recipe_ingredients").fetchone()[0]

    print(f"Before: {before} ingredients")
    print(f"Merged: {merged} duplicate rows deleted")
    print(f"After:  {after} ingredients")
    print(f"Recipe-ingredient links: {ri} (should be unchanged)")

    db.close()


if __name__ == "__main__":
    main()
