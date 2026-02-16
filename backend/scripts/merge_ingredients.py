#!/usr/bin/env python3
"""Merge duplicate / near-duplicate ingredients in master_data.json.

For each merge group the script:
  1. Picks a canonical ingredient entry (best metadata wins).
  2. Rewrites every recipe ingredient reference to the canonical name.
  3. Removes the duplicate ingredient entries.
  4. Writes the updated master_data.json.
  5. Prints a SQL migration you can run against the live DB.

Usage:
    python backend/scripts/merge_ingredients.py          # dry-run (prints changes)
    python backend/scripts/merge_ingredients.py --apply   # writes master_data.json + SQL file
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MASTER_DATA = Path(__file__).resolve().parent.parent / "seeds" / "master_data.json"
SQL_OUT = Path(__file__).resolve().parent.parent / "scripts" / "merge_ingredients.sql"

# ── Merge groups ─────────────────────────────────────────────────────────────
# canonical_name → [all names that should collapse into it]
# The canonical name MUST appear in the list.
MERGE_GROUPS: dict[str, list[str]] = {
    # Tea
    "Black tea": ["black tea loose leaf", "black tea powder dust", "loose leaf black tea"],

    # Herbs & aromatics
    "Bay leaves": ["Bay leaf", "bay leaves"],
    "Cilantro": ["Cilantro", "Fresh cilantro"],
    "Ginger": ["Ginger", "Fresh ginger"],
    "Mint": ["Mint", "fresh mint", "fresh mint leaves", "mint leaves"],
    "Garlic": ["Garlic", "garlic cloves"],

    # Spices (ground)
    "Coriander powder": ["Coriander powder", "Ground coriander"],
    "Cardamom powder": ["cardamom powder", "ground cardamom"],
    "Red chili powder": ["Red chili powder", "Red chilly powder"],
    "Ground cumin": ["Ground cumin", "Roasted ground cumin", "Jeera Powder"],
    "Turmeric": ["Turmeric", "Turmeric Powder"],
    "Fenugreek powder": ["fenugreek powder", "roasted fenugreek powder"],
    "Amchur": ["dried raw mango powder", "Dried raw mango powder (amchur)"],
    "Nutmeg": ["nutmeg", "Nutmeg (whole)"],
    "Mustard powder": ["raw mustard powder", "mustard seed powder"],

    # Spices (whole)
    "Cardamom": ["Cardamom", "cardamom pods", "whole cardamom pods"],
    "Cumin seeds": ["Cumin seeds", "Jeera"],
    "Cinnamon": ["Cinnamon", "cinnamon stick"],
    "Cloves": ["Cloves", "whole cloves"],
    "Black pepper": ["Black pepper", "black peppercorns"],
    "Kasuri methi": ["Kasuri methi", "dried fenugreek leaves", "Dried fenugreek leaves (kasuri methi)"],
    "Fenugreek seeds": ["Fenugreek", "Methi seeds"],
    "Panch phoran": ["Panch phoran", "panch phoron"],
    "Ajwain": ["Ajwain", "carom seeds"],
    "Asafoetida (hing)": ["Asafoetida (hing)", "Hing"],
    "Saffron": ["Saffron", "saffron strands"],

    # Spice blends
    "Besan": ["Besan", "gram flour"],

    # Chilies
    "Green chilies": ["Green chilies", "Green chillies", "Thai green chili", "Thai green chilies"],
    "Dried red chilies": ["Dried red chilies", "Red chillies"],

    # Produce - vegetables
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

    # Nuts & seeds
    "Cashews": ["Cashew", "Cashews", "cashew nuts"],
    "Crushed roasted peanuts": ["Coarsely crushed roasted peanuts", "Crushed roasted peanuts"],

    # Coconut forms
    "Dried coconut slices": ["dried coconut slices", "Dry Coconut Slices"],
    "Frozen coconut": ["Frozen coconut", "frozen fine-textured coconut", "frozen shredded coconut"],
    "Sesame oil": ["Sesame (Gingelly) Oil", "sesame oil"],

    # Dried fruit
    "Raisins": ["Raisin", "Raisins"],

    # Lentils / dal
    "Green mung dal": ["green moong dal", "Green Mung Dal"],
    "Whole green mung": ["Whole green moong", "Whole Green Mung"],
    "Yellow moong dal": ["yellow moong dal", "Yellow split moong dal"],
    "Masoor dal": ["Masoor dal", "split masoor dal"],
    "Black chana": ["Black chana", "black chana dried"],
    "Tamarind": ["Tamarind", "raw tamarind"],

    # Grains
    "Sona Masoori Rice": ["Rice (Sona Masoori)", "Sona Masoori Rice"],
    "Sooji": ["Sooji", "Cream of Wheat (sooji)"],
    "Rolled oats": ["Organic rolled oats", "Rolled Oats"],
    "Khakhra": ["Khakhra", "Khakra"],

    # Citrus
    "Lemon or lime": ["Lemon or lime", "Lemon or lime juice", "Lime or lemon"],

    # Coffee
    "Filter coffee": ["filter coffee", "Filter Coffee"],
}


def build_rename_map(groups: dict[str, list[str]]) -> dict[str, str]:
    """old_name (case-insensitive key) → canonical_name."""
    rename = {}
    for canonical, aliases in groups.items():
        for alias in aliases:
            key = alias.lower()
            if key in rename and rename[key] != canonical:
                raise ValueError(
                    f"Conflict: '{alias}' mapped to both "
                    f"'{rename[key]}' and '{canonical}'"
                )
            rename[key] = canonical
    return rename


def best_ingredient(entries: list[dict]) -> dict:
    """Pick the entry with the most metadata filled in."""
    def score(e: dict) -> int:
        s = 0
        if e.get("category"): s += 2
        if e.get("canonical_unit"): s += 1
        if e.get("grams_per_cup") is not None: s += 1
        if e.get("purchase_tier"): s += 1
        if e.get("notes"): s += 1
        return s
    return max(entries, key=score)


def merge(data: dict, dry_run: bool = True) -> tuple[dict, list[str]]:
    rename_map = build_rename_map(MERGE_GROUPS)
    sql_lines: list[str] = []

    # ── 1. Deduplicate ingredient list ────────────────────────────────────
    seen: dict[str, dict] = {}  # canonical_lower → entry
    removed_ingredients: list[str] = []

    for ing in data["ingredients"]:
        name = ing["name"]
        canonical = rename_map.get(name.lower(), name)
        key = canonical.lower()

        if key in seen:
            # Merge metadata: keep the richer entry
            existing = seen[key]
            candidate = dict(ing, name=canonical)
            winner = best_ingredient([existing, candidate])
            winner["name"] = canonical
            seen[key] = winner
            if name.lower() != canonical.lower():
                removed_ingredients.append(name)
        else:
            seen[key] = dict(ing, name=canonical)
            if name != canonical:
                removed_ingredients.append(name)

    new_ingredients = sorted(seen.values(), key=lambda x: x["name"].lower())

    # ── 2. Rewrite recipe ingredient references ──────────────────────────
    recipe_renames: list[tuple[str, str, str]] = []  # (recipe, old, new)

    for recipe in data["recipes"]:
        for ri in recipe.get("ingredients", []):
            old_name = ri["ingredient_name"]
            canonical = rename_map.get(old_name.lower())
            if canonical and canonical != old_name:
                recipe_renames.append((recipe["name"], old_name, canonical))
                ri["ingredient_name"] = canonical

    # ── 3. Report ────────────────────────────────────────────────────────
    print(f"\n{'DRY RUN' if dry_run else 'APPLYING'}")
    print(f"  Ingredients before: {len(data['ingredients'])}")
    print(f"  Ingredients after:  {len(new_ingredients)}")
    print(f"  Ingredients removed: {len(data['ingredients']) - len(new_ingredients)}")
    print(f"  Recipe references rewritten: {len(recipe_renames)}")

    if removed_ingredients:
        print("\n  Removed / renamed ingredients:")
        for name in sorted(set(removed_ingredients)):
            canonical = rename_map.get(name.lower(), name)
            print(f"    {name} → {canonical}")

    if recipe_renames:
        print(f"\n  Recipe ingredient renames ({len(recipe_renames)}):")
        for rname, old, new in sorted(recipe_renames):
            print(f"    [{rname}] {old} → {new}")

    # ── 4. Generate SQL ──────────────────────────────────────────────────
    sql_lines.append("-- Auto-generated ingredient merge migration")
    sql_lines.append(f"-- Generated: {datetime.now(timezone.utc).isoformat()}")
    sql_lines.append("-- Run against the live retreat_ops.db\n")
    sql_lines.append("PRAGMA foreign_keys = ON;")
    sql_lines.append("BEGIN TRANSACTION;\n")

    for canonical, aliases in sorted(MERGE_GROUPS.items()):
        others = [a for a in aliases if a.lower() != canonical.lower()]
        if not others:
            # Only a rename (single entry)
            for a in aliases:
                if a != canonical:
                    sql_lines.append(
                        f"-- Rename '{a}' → '{canonical}'"
                    )
                    sql_lines.append(
                        f"UPDATE ingredients SET name = '{_esc(canonical)}' "
                        f"WHERE lower(name) = lower('{_esc(a)}');"
                    )
            continue

        sql_lines.append(f"\n-- Merge group: {canonical}")

        # Ensure canonical row exists (rename first match if needed)
        first_alias = aliases[0]
        if first_alias.lower() != canonical.lower():
            # If the canonical name doesn't exist yet, rename the first alias
            sql_lines.append(
                f"UPDATE OR IGNORE ingredients SET name = '{_esc(canonical)}' "
                f"WHERE lower(name) = lower('{_esc(first_alias)}') "
                f"AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('{_esc(canonical)}'));"
            )

        for alias in aliases:
            if alias.lower() == canonical.lower():
                continue
            # Move recipe_ingredients refs to canonical
            sql_lines.append(
                f"UPDATE recipe_ingredients SET ingredient_id = "
                f"(SELECT id FROM ingredients WHERE lower(name) = lower('{_esc(canonical)}')) "
                f"WHERE ingredient_id = "
                f"(SELECT id FROM ingredients WHERE lower(name) = lower('{_esc(alias)}'));"
            )
            # Move shopping_list_items refs
            sql_lines.append(
                f"UPDATE shopping_list_items SET ingredient_id = "
                f"(SELECT id FROM ingredients WHERE lower(name) = lower('{_esc(canonical)}')) "
                f"WHERE ingredient_id = "
                f"(SELECT id FROM ingredients WHERE lower(name) = lower('{_esc(alias)}'));"
            )
            # Move inventory_items refs
            sql_lines.append(
                f"UPDATE inventory_items SET ingredient_id = "
                f"(SELECT id FROM ingredients WHERE lower(name) = lower('{_esc(canonical)}')) "
                f"WHERE ingredient_id = "
                f"(SELECT id FROM ingredients WHERE lower(name) = lower('{_esc(alias)}'));"
            )
            # Delete the old ingredient
            sql_lines.append(
                f"DELETE FROM ingredients WHERE lower(name) = lower('{_esc(alias)}');"
            )

    sql_lines.append("\nCOMMIT;")
    sql_lines.append("")

    data["ingredients"] = new_ingredients
    return data, sql_lines


def _esc(s: str) -> str:
    return s.replace("'", "''")


def main():
    dry_run = "--apply" not in sys.argv

    with open(MASTER_DATA) as f:
        data = json.load(f)

    data, sql_lines = merge(data, dry_run=dry_run)

    if dry_run:
        print("\nRe-run with --apply to write changes.")
    else:
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        with open(MASTER_DATA, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"\n  Wrote {MASTER_DATA}")

        with open(SQL_OUT, "w") as f:
            f.write("\n".join(sql_lines))
        print(f"  Wrote {SQL_OUT}")
        print(f"\n  To apply to live DB:")
        print(f"    sqlite3 backend/retreat_ops.db < {SQL_OUT}")


if __name__ == "__main__":
    main()
