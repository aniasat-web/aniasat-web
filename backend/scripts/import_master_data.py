from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow `python scripts/import_master_data.py` from backend/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import get_connection, init_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import master data JSON into DB (recipes, ingredients, unit conversions)."
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=ROOT / "seeds" / "master_data.json",
        help="Seed JSON path (default: backend/seeds/master_data.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report import results without committing changes.",
    )
    return parser.parse_args()


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def as_positive_float(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric (got {value!r})") from exc
    if number <= 0:
        raise ValueError(f"{field} must be > 0 (got {number})")
    return number


def upsert_ingredient(conn: Any, ingredient: dict[str, Any]) -> int:
    name = clean_text(ingredient.get("name"))
    if not name:
        raise ValueError("Ingredient name is required")

    category = clean_text(ingredient.get("category"))
    purchase_tier = clean_text(ingredient.get("purchase_tier"))
    canonical_unit = clean_text(ingredient.get("canonical_unit"))
    grams_per_cup_raw = ingredient.get("grams_per_cup")
    grams_per_cup = float(grams_per_cup_raw) if grams_per_cup_raw is not None else None
    notes = clean_text(ingredient.get("notes"))

    existing = conn.execute(
        "SELECT id FROM ingredients WHERE lower(name) = lower(?)",
        (name,),
    ).fetchone()
    if existing:
        ingredient_id = int(existing["id"])
        conn.execute(
            """
            UPDATE ingredients
            SET name = ?, category = ?, purchase_tier = ?, canonical_unit = ?, grams_per_cup = ?, notes = ?
            WHERE id = ?
            """,
            (name, category, purchase_tier, canonical_unit, grams_per_cup, notes, ingredient_id),
        )
        return ingredient_id

    row = conn.execute(
        """
        INSERT INTO ingredients(name, category, purchase_tier, canonical_unit, grams_per_cup, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (name, category, purchase_tier, canonical_unit, grams_per_cup, notes),
    ).fetchone()
    return int(row["id"])


def get_or_create_ingredient_id(
    conn: Any,
    ingredient_name: str,
    ingredient_seed_index: dict[str, dict[str, Any]],
) -> int:
    existing = conn.execute(
        "SELECT id FROM ingredients WHERE lower(name) = lower(?)",
        (ingredient_name,),
    ).fetchone()
    if existing:
        return int(existing["id"])

    seed_match = ingredient_seed_index.get(ingredient_name.lower())
    if seed_match:
        return upsert_ingredient(conn, seed_match)

    return upsert_ingredient(conn, {"name": ingredient_name})


def import_unit_conversions(conn: Any, rows: list[dict[str, Any]]) -> int:
    conn.execute("DELETE FROM unit_conversions")

    inserted = 0
    for row in rows:
        quantity_from = as_positive_float(row.get("quantity_from"), "unit_conversions.quantity_from")
        quantity_to = as_positive_float(row.get("quantity_to"), "unit_conversions.quantity_to")
        unit_from = clean_text(row.get("unit_from"))
        unit_to = clean_text(row.get("unit_to"))
        context = clean_text(row.get("context"))
        if not unit_from or not unit_to or not context:
            raise ValueError("unit_conversions rows require unit_from, unit_to, and context")

        source_row_raw = row.get("source_row")
        source_row = int(source_row_raw) if source_row_raw is not None else None

        conn.execute(
            """
            INSERT INTO unit_conversions(
                item_name,
                quantity_from,
                unit_from,
                quantity_to,
                unit_to,
                context,
                source_sheet,
                source_row,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_text(row.get("item_name")),
                quantity_from,
                unit_from,
                quantity_to,
                unit_to,
                context,
                clean_text(row.get("source_sheet")),
                source_row,
                clean_text(row.get("notes")),
            ),
        )
        inserted += 1
    return inserted


def upsert_recipe(
    conn: Any,
    recipe: dict[str, Any],
    ingredient_seed_index: dict[str, dict[str, Any]],
) -> int:
    recipe_name = clean_text(recipe.get("name"))
    if not recipe_name:
        raise ValueError("Recipe name is required")

    base_servings = as_positive_float(recipe.get("base_servings"), f"recipes[{recipe_name}].base_servings")
    category = clean_text(recipe.get("category"))
    notes = clean_text(recipe.get("notes"))

    existing = conn.execute(
        "SELECT id FROM recipes WHERE lower(name) = lower(?)",
        (recipe_name,),
    ).fetchone()
    if existing:
        recipe_id = int(existing["id"])
        conn.execute(
            """
            UPDATE recipes
            SET name = ?, category = ?, base_servings = ?, notes = ?
            WHERE id = ?
            """,
            (recipe_name, category, base_servings, notes, recipe_id),
        )
    else:
        created = conn.execute(
            """
            INSERT INTO recipes(name, category, base_servings, notes)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            (recipe_name, category, base_servings, notes),
        ).fetchone()
        recipe_id = int(created["id"])

    conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
    conn.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", (recipe_id,))

    ingredients = recipe.get("ingredients") or []
    if not isinstance(ingredients, list):
        raise ValueError(f"Recipe {recipe_name!r}: ingredients must be a list")

    for item in ingredients:
        if not isinstance(item, dict):
            raise ValueError(f"Recipe {recipe_name!r}: ingredient item must be an object")
        ingredient_name = clean_text(item.get("ingredient_name"))
        if not ingredient_name:
            raise ValueError(f"Recipe {recipe_name!r}: ingredient_name is required")
        quantity = as_positive_float(item.get("quantity"), f"{recipe_name}.{ingredient_name}.quantity")
        unit = clean_text(item.get("unit"))
        if not unit:
            raise ValueError(f"Recipe {recipe_name!r}: unit required for ingredient {ingredient_name!r}")

        ingredient_id = get_or_create_ingredient_id(conn, ingredient_name, ingredient_seed_index)
        conn.execute(
            """
            INSERT INTO recipe_ingredients(recipe_id, ingredient_id, quantity, unit, prep_notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (recipe_id, ingredient_id, quantity, unit, clean_text(item.get("prep_notes"))),
        )

    steps = recipe.get("steps") or []
    if not isinstance(steps, list):
        raise ValueError(f"Recipe {recipe_name!r}: steps must be a list")
    step_order = 1
    for step in steps:
        instruction = clean_text(step)
        if not instruction:
            continue
        conn.execute(
            """
            INSERT INTO recipe_steps(recipe_id, step_order, instruction)
            VALUES (?, ?, ?)
            """,
            (recipe_id, step_order, instruction),
        )
        step_order += 1

    return recipe_id


def main() -> int:
    args = parse_args()
    init_db()

    if not args.seed.exists():
        raise FileNotFoundError(f"Seed file not found: {args.seed}")

    with args.seed.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("format") != "retreat_ops_master_data":
        raise ValueError(
            "Seed JSON format mismatch: expected format='retreat_ops_master_data'"
        )
    if int(payload.get("version", 0)) != 1:
        raise ValueError("Seed JSON version mismatch: expected version=1")

    ingredients = payload.get("ingredients") or []
    unit_conversions = payload.get("unit_conversions") or []
    recipes = payload.get("recipes") or []
    if not isinstance(ingredients, list) or not isinstance(unit_conversions, list) or not isinstance(recipes, list):
        raise ValueError("Seed JSON must provide list fields: ingredients, unit_conversions, recipes")

    ingredient_seed_index: dict[str, dict[str, Any]] = {}
    for row in ingredients:
        if not isinstance(row, dict):
            raise ValueError("ingredients list must contain objects")
        name = clean_text(row.get("name"))
        if not name:
            raise ValueError("ingredients row missing required name")
        ingredient_seed_index[name.lower()] = row

    with get_connection() as conn:
        imported_ingredients = 0
        imported_recipes = 0

        for row in ingredients:
            upsert_ingredient(conn, row)
            imported_ingredients += 1

        imported_conversions = import_unit_conversions(conn, unit_conversions)

        for row in recipes:
            if not isinstance(row, dict):
                raise ValueError("recipes list must contain objects")
            upsert_recipe(conn, row, ingredient_seed_index)
            imported_recipes += 1

        if args.dry_run:
            conn.rollback()
            mode = "DRY RUN"
        else:
            conn.commit()
            mode = "COMMITTED"

    print(
        f"[{mode}] imported master data from {args.seed}: "
        f"ingredients={imported_ingredients}, "
        f"unit_conversions={imported_conversions}, "
        f"recipes={imported_recipes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
