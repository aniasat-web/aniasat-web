from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow `python scripts/export_master_data.py` from backend/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import DB_PATH, get_connection, init_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export master data (recipes, ingredients, unit conversions) to JSON."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "seeds" / "master_data.json",
        help="Output JSON file path (default: backend/seeds/master_data.json).",
    )
    return parser.parse_args()


def fetch_ingredients(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT name, category, purchase_tier, canonical_unit, grams_per_cup, notes
        FROM ingredients
        ORDER BY lower(name), id
        """
    ).fetchall()
    return [
        {
            "name": row["name"],
            "category": row["category"],
            "purchase_tier": row["purchase_tier"],
            "canonical_unit": row["canonical_unit"],
            "grams_per_cup": float(row["grams_per_cup"]) if row["grams_per_cup"] is not None else None,
            "notes": row["notes"],
        }
        for row in rows
    ]


def fetch_unit_conversions(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            item_name,
            quantity_from,
            unit_from,
            quantity_to,
            unit_to,
            context,
            source_sheet,
            source_row,
            notes
        FROM unit_conversions
        ORDER BY lower(coalesce(context, '')), lower(coalesce(item_name, '')), lower(unit_from), id
        """
    ).fetchall()
    return [
        {
            "item_name": row["item_name"],
            "quantity_from": float(row["quantity_from"]),
            "unit_from": row["unit_from"],
            "quantity_to": float(row["quantity_to"]),
            "unit_to": row["unit_to"],
            "context": row["context"],
            "source_sheet": row["source_sheet"],
            "source_row": int(row["source_row"]) if row["source_row"] is not None else None,
            "notes": row["notes"],
        }
        for row in rows
    ]


def fetch_recipes(conn: Any) -> list[dict[str, Any]]:
    recipe_rows = conn.execute(
        """
        SELECT id, name, category, base_servings, notes
        FROM recipes
        ORDER BY lower(name), id
        """
    ).fetchall()

    ingredients_rows = conn.execute(
        """
        SELECT
            ri.recipe_id,
            i.name AS ingredient_name,
            ri.quantity,
            ri.unit,
            ri.prep_notes
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        ORDER BY ri.recipe_id, ri.id
        """
    ).fetchall()

    steps_rows = conn.execute(
        """
        SELECT recipe_id, step_order, instruction
        FROM recipe_steps
        ORDER BY recipe_id, step_order, id
        """
    ).fetchall()

    ingredients_by_recipe: dict[int, list[dict[str, Any]]] = {}
    for row in ingredients_rows:
        recipe_id = int(row["recipe_id"])
        ingredients_by_recipe.setdefault(recipe_id, []).append(
            {
                "ingredient_name": row["ingredient_name"],
                "quantity": float(row["quantity"]),
                "unit": row["unit"],
                "prep_notes": row["prep_notes"],
            }
        )

    steps_by_recipe: dict[int, list[str]] = {}
    for row in steps_rows:
        recipe_id = int(row["recipe_id"])
        steps_by_recipe.setdefault(recipe_id, []).append(row["instruction"])

    recipes: list[dict[str, Any]] = []
    for row in recipe_rows:
        recipe_id = int(row["id"])
        recipes.append(
            {
                "name": row["name"],
                "category": row["category"],
                "base_servings": float(row["base_servings"]),
                "notes": row["notes"],
                "ingredients": ingredients_by_recipe.get(recipe_id, []),
                "steps": steps_by_recipe.get(recipe_id, []),
            }
        )
    return recipes


def main() -> int:
    args = parse_args()
    init_db()

    with get_connection() as conn:
        ingredients = fetch_ingredients(conn)
        unit_conversions = fetch_unit_conversions(conn)
        recipes = fetch_recipes(conn)

    payload = {
        "format": "retreat_ops_master_data",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_db": "backend/data/retreat_ops.db",
        "ingredients": ingredients,
        "unit_conversions": unit_conversions,
        "recipes": recipes,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    print(
        "Exported master data:"
        f" ingredients={len(ingredients)}"
        f" unit_conversions={len(unit_conversions)}"
        f" recipes={len(recipes)}"
        f" -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
