from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/seed_demo_data.py` from backend/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import get_connection, init_db


def upsert_ingredient(name: str, canonical_unit: str | None, grams_per_cup: float | None) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM ingredients WHERE lower(name)=lower(?)", (name,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE ingredients SET canonical_unit=?, grams_per_cup=? WHERE id=?",
                (canonical_unit, grams_per_cup, row["id"]),
            )
            conn.commit()
            return int(row["id"])

        row = conn.execute(
            "INSERT INTO ingredients(name, canonical_unit, grams_per_cup) VALUES (?, ?, ?) RETURNING id",
            (name, canonical_unit, grams_per_cup),
        ).fetchone()
        conn.commit()
        return int(row["id"])


def main() -> None:
    init_db()

    ingredients = {
        "Rolled Oats": ("g", 90.0),
        "Milk": ("ml", 245.0),
        "Rice (Sona Masoori)": ("g", 185.0),
        "Toor Dal": ("g", 200.0),
        "Cilantro": ("bunches", None),
    }

    ids: dict[str, int] = {}
    for name, (canon, gpc) in ingredients.items():
        ids[name] = upsert_ingredient(name, canon, gpc)

    with get_connection() as conn:
        recipe = conn.execute(
            "SELECT id FROM recipes WHERE lower(name)=lower('Chai')"
        ).fetchone()
        if not recipe:
            recipe = conn.execute(
                "INSERT INTO recipes(name, base_servings, notes) VALUES (?, ?, ?) RETURNING id",
                ("Chai", 6.0, "Sample recipe for local testing."),
            ).fetchone()
            recipe_id = int(recipe["id"])

            rows = [
                (recipe_id, ids["Milk"], 2.0, "cup", ""),
                (recipe_id, ids["Rolled Oats"], 0.5, "cup", "Example dry-good item"),
            ]
            conn.executemany(
                """
                INSERT INTO recipe_ingredients(recipe_id, ingredient_id, quantity, unit, prep_notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

        conn.commit()

    print("Seeded demo data.")


if __name__ == "__main__":
    main()
