from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "retreat_ops.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
MASTER_SEED_PATH = PROJECT_ROOT / "seeds" / "master_data.json"
AUTO_SEED_MASTER_DATA_ENV = "RETREAT_OPS_AUTO_SEED_MASTER_DATA"
AUTO_SEED_DISABLED_VALUES = {"0", "false", "off", "no"}

LOGGER = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)

        ingredient_columns = {row[1] for row in conn.execute("PRAGMA table_info(ingredients)").fetchall()}
        if "category" not in ingredient_columns:
            conn.execute("ALTER TABLE ingredients ADD COLUMN category TEXT")

        if "purchase_tier" not in ingredient_columns:
            conn.execute("ALTER TABLE ingredients ADD COLUMN purchase_tier TEXT")
            conn.execute(
                """
                UPDATE ingredients SET purchase_tier = 'bulk'
                WHERE category IN (
                    'Grains & Flours', 'Pulses & Legumes', 'Spices & Seasonings',
                    'Nuts & Seeds', 'Oils & Fats', 'Pantry Staples',
                    'Sweeteners', 'Condiments & Sauces', 'Beverages'
                ) AND purchase_tier IS NULL
                """
            )
            conn.execute(
                """
                UPDATE ingredients SET purchase_tier = 'fresh'
                WHERE category IN ('Produce', 'Herbs', 'Dairy & Refrigerated')
                AND purchase_tier IS NULL
                """
            )

        recipe_columns = {row[1] for row in conn.execute("PRAGMA table_info(recipes)").fetchall()}
        if "category" not in recipe_columns:
            conn.execute("ALTER TABLE recipes ADD COLUMN category TEXT")

        columns = {row[1] for row in conn.execute("PRAGMA table_info(service_snapshots)").fetchall()}
        if "retreat_plan_id" not in columns:
            conn.execute(
                "ALTER TABLE service_snapshots ADD COLUMN retreat_plan_id INTEGER REFERENCES retreat_plans(id) ON DELETE SET NULL"
            )

        maybe_seed_master_data(conn)
        conn.commit()


def maybe_seed_master_data(conn: sqlite3.Connection) -> None:
    if not auto_seed_master_data_enabled():
        return

    master_counts = read_master_data_counts(conn)
    if any(master_counts.values()):
        return

    if not MASTER_SEED_PATH.exists():
        LOGGER.info(
            "Master seed not found at %s; startup will use empty master data.",
            MASTER_SEED_PATH,
        )
        return

    payload = json.loads(MASTER_SEED_PATH.read_text(encoding="utf-8"))
    imported = apply_master_seed_payload(conn, payload)
    LOGGER.info(
        "Auto-seeded master data from %s (ingredients=%d, unit_conversions=%d, recipes=%d).",
        MASTER_SEED_PATH,
        imported["ingredients"],
        imported["unit_conversions"],
        imported["recipes"],
    )


def auto_seed_master_data_enabled() -> bool:
    raw_value = os.getenv(AUTO_SEED_MASTER_DATA_ENV, "1").strip().lower()
    return raw_value not in AUTO_SEED_DISABLED_VALUES


def read_master_data_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "ingredients": table_count(conn, "ingredients"),
        "unit_conversions": table_count(conn, "unit_conversions"),
        "recipes": table_count(conn, "recipes"),
    }


def table_count(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}").fetchone()
    return int(row["row_count"]) if row else 0


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def as_positive_float(value: object, field_name: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric (got {value!r})") from exc

    if numeric <= 0:
        raise ValueError(f"{field_name} must be > 0 (got {numeric})")
    return numeric


def as_optional_float(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric or null (got {value!r})") from exc


def apply_master_seed_payload(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, int]:
    if payload.get("format") != "retreat_ops_master_data":
        raise ValueError("Seed JSON format mismatch: expected format='retreat_ops_master_data'")

    seed_version = int(payload.get("version", 0))
    if seed_version != 1:
        raise ValueError("Seed JSON version mismatch: expected version=1")

    ingredients = payload.get("ingredients")
    unit_conversions = payload.get("unit_conversions")
    recipes = payload.get("recipes")
    if not isinstance(ingredients, list):
        raise ValueError("Seed field 'ingredients' must be a list")
    if not isinstance(unit_conversions, list):
        raise ValueError("Seed field 'unit_conversions' must be a list")
    if not isinstance(recipes, list):
        raise ValueError("Seed field 'recipes' must be a list")

    ingredient_index: dict[str, dict[str, Any]] = {}
    ingredient_count = 0
    for item in ingredients:
        if not isinstance(item, dict):
            raise ValueError("Each item in 'ingredients' must be an object")
        ingredient_name = clean_text(item.get("name"))
        if not ingredient_name:
            raise ValueError("Each ingredient must include a non-empty name")
        ingredient_index[ingredient_name.lower()] = item
        upsert_ingredient(conn, item)
        ingredient_count += 1

    conversion_count = replace_unit_conversions(conn, unit_conversions)

    recipe_count = 0
    for recipe in recipes:
        if not isinstance(recipe, dict):
            raise ValueError("Each item in 'recipes' must be an object")
        upsert_recipe(conn, recipe, ingredient_index)
        recipe_count += 1

    return {
        "ingredients": ingredient_count,
        "unit_conversions": conversion_count,
        "recipes": recipe_count,
    }


def upsert_ingredient(conn: sqlite3.Connection, ingredient: dict[str, Any]) -> int:
    ingredient_name = clean_text(ingredient.get("name"))
    if not ingredient_name:
        raise ValueError("Ingredient name is required")

    category = clean_text(ingredient.get("category"))
    purchase_tier = clean_text(ingredient.get("purchase_tier"))
    canonical_unit = clean_text(ingredient.get("canonical_unit"))
    grams_per_cup = as_optional_float(ingredient.get("grams_per_cup"), "ingredient.grams_per_cup")
    notes = clean_text(ingredient.get("notes"))

    existing = conn.execute(
        "SELECT id FROM ingredients WHERE lower(name) = lower(?)",
        (ingredient_name,),
    ).fetchone()
    if existing:
        ingredient_id = int(existing["id"])
        conn.execute(
            """
            UPDATE ingredients
            SET name = ?, category = ?, purchase_tier = ?, canonical_unit = ?, grams_per_cup = ?, notes = ?
            WHERE id = ?
            """,
            (ingredient_name, category, purchase_tier, canonical_unit, grams_per_cup, notes, ingredient_id),
        )
        return ingredient_id

    created = conn.execute(
        """
        INSERT INTO ingredients(name, category, purchase_tier, canonical_unit, grams_per_cup, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (ingredient_name, category, purchase_tier, canonical_unit, grams_per_cup, notes),
    ).fetchone()
    return int(created["id"])


def get_or_create_ingredient_id(
    conn: sqlite3.Connection, ingredient_name: str, ingredient_index: dict[str, dict[str, Any]]
) -> int:
    existing = conn.execute(
        "SELECT id FROM ingredients WHERE lower(name) = lower(?)",
        (ingredient_name,),
    ).fetchone()
    if existing:
        return int(existing["id"])

    seed_ingredient = ingredient_index.get(ingredient_name.lower())
    if seed_ingredient:
        return upsert_ingredient(conn, seed_ingredient)

    return upsert_ingredient(conn, {"name": ingredient_name})


def replace_unit_conversions(conn: sqlite3.Connection, unit_conversions: list[dict[str, Any]]) -> int:
    conn.execute("DELETE FROM unit_conversions")
    inserted = 0

    for row in unit_conversions:
        if not isinstance(row, dict):
            raise ValueError("Each item in 'unit_conversions' must be an object")

        quantity_from = as_positive_float(row.get("quantity_from"), "unit_conversions.quantity_from")
        quantity_to = as_positive_float(row.get("quantity_to"), "unit_conversions.quantity_to")
        unit_from = clean_text(row.get("unit_from"))
        unit_to = clean_text(row.get("unit_to"))
        context = clean_text(row.get("context"))

        if not unit_from or not unit_to or not context:
            raise ValueError("Each unit conversion must include unit_from, unit_to, and context")

        source_row_value = row.get("source_row")
        source_row = int(source_row_value) if source_row_value is not None else None

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
    conn: sqlite3.Connection,
    recipe: dict[str, Any],
    ingredient_index: dict[str, dict[str, Any]],
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

    for ingredient in ingredients:
        if not isinstance(ingredient, dict):
            raise ValueError(f"Recipe {recipe_name!r}: ingredient items must be objects")

        ingredient_name = clean_text(ingredient.get("ingredient_name"))
        if not ingredient_name:
            raise ValueError(f"Recipe {recipe_name!r}: ingredient_name is required")
        quantity = as_positive_float(
            ingredient.get("quantity"),
            f"recipes[{recipe_name}].ingredients[{ingredient_name}].quantity",
        )
        unit = clean_text(ingredient.get("unit"))
        if not unit:
            raise ValueError(f"Recipe {recipe_name!r}: unit is required for ingredient {ingredient_name!r}")

        ingredient_id = get_or_create_ingredient_id(conn, ingredient_name, ingredient_index)
        conn.execute(
            """
            INSERT INTO recipe_ingredients(recipe_id, ingredient_id, quantity, unit, prep_notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (recipe_id, ingredient_id, quantity, unit, clean_text(ingredient.get("prep_notes"))),
        )

    steps = recipe.get("steps") or []
    if not isinstance(steps, list):
        raise ValueError(f"Recipe {recipe_name!r}: steps must be a list")
    for step_order, step_text in enumerate(steps, start=1):
        instruction = clean_text(step_text)
        if not instruction:
            continue
        conn.execute(
            """
            INSERT INTO recipe_steps(recipe_id, step_order, instruction)
            VALUES (?, ?, ?)
            """,
            (recipe_id, step_order, instruction),
        )

    return recipe_id
