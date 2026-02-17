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


def fetch_vendors(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT name, notes
        FROM vendors
        ORDER BY lower(name), id
        """
    ).fetchall()
    return [{"name": row["name"], "notes": row["notes"]} for row in rows]


def fetch_retreat_plans(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT name, start_date, day_count, default_people, plan_json, created_at, updated_at
        FROM retreat_plans
        ORDER BY created_at, id
        """
    ).fetchall()
    return [
        {
            "name": row["name"],
            "start_date": row["start_date"],
            "day_count": int(row["day_count"]),
            "default_people": float(row["default_people"]),
            "plan_json": row["plan_json"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def fetch_inventory_items(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT i.name AS ingredient_name, inv.quantity, inv.unit, inv.source, inv.updated_at
        FROM inventory_items inv
        JOIN ingredients i ON i.id = inv.ingredient_id
        ORDER BY lower(i.name), inv.id
        """
    ).fetchall()
    return [
        {
            "ingredient_name": row["ingredient_name"],
            "quantity": float(row["quantity"]),
            "unit": row["unit"],
            "source": row["source"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def fetch_shopping_lists(conn: Any) -> list[dict[str, Any]]:
    list_rows = conn.execute(
        """
        SELECT sl.id, sl.name, sl.phase, sl.status, sl.created_at,
               rp.name AS retreat_plan_name
        FROM shopping_lists sl
        LEFT JOIN retreat_plans rp ON rp.id = sl.retreat_plan_id
        ORDER BY sl.created_at, sl.id
        """
    ).fetchall()

    item_rows = conn.execute(
        """
        SELECT
            sli.shopping_list_id,
            i.name AS ingredient_name,
            v.name AS vendor_name,
            sli.required_qty,
            sli.required_unit,
            sli.in_stock_qty,
            sli.in_stock_unit,
            sli.to_buy_qty,
            sli.to_buy_unit,
            sli.owner,
            sli.pickup_date,
            sli.ordered,
            sli.ordered_at,
            sli.received,
            sli.received_at,
            sli.status,
            sli.notes
        FROM shopping_list_items sli
        JOIN ingredients i ON i.id = sli.ingredient_id
        LEFT JOIN vendors v ON v.id = sli.vendor_id
        ORDER BY sli.shopping_list_id, sli.id
        """
    ).fetchall()

    items_by_list: dict[int, list[dict[str, Any]]] = {}
    for row in item_rows:
        list_id = int(row["shopping_list_id"])
        items_by_list.setdefault(list_id, []).append(
            {
                "ingredient_name": row["ingredient_name"],
                "vendor_name": row["vendor_name"],
                "required_qty": float(row["required_qty"]),
                "required_unit": row["required_unit"],
                "in_stock_qty": float(row["in_stock_qty"]) if row["in_stock_qty"] is not None else None,
                "in_stock_unit": row["in_stock_unit"],
                "to_buy_qty": float(row["to_buy_qty"]) if row["to_buy_qty"] is not None else None,
                "to_buy_unit": row["to_buy_unit"],
                "owner": row["owner"],
                "pickup_date": row["pickup_date"],
                "ordered": int(row["ordered"]),
                "ordered_at": row["ordered_at"],
                "received": int(row["received"]),
                "received_at": row["received_at"],
                "status": row["status"],
                "notes": row["notes"],
            }
        )

    results: list[dict[str, Any]] = []
    total_items = 0
    for row in list_rows:
        list_id = int(row["id"])
        items = items_by_list.get(list_id, [])
        total_items += len(items)
        results.append(
            {
                "name": row["name"],
                "phase": row["phase"],
                "status": row["status"],
                "retreat_plan_name": row["retreat_plan_name"],
                "created_at": row["created_at"],
                "items": items,
            }
        )
    return results


def fetch_service_snapshots(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT ss.retreat_name, ss.payload_json, ss.created_at,
               rp.name AS retreat_plan_name
        FROM service_snapshots ss
        LEFT JOIN retreat_plans rp ON rp.id = ss.retreat_plan_id
        ORDER BY ss.created_at, ss.id
        """
    ).fetchall()
    return [
        {
            "retreat_name": row["retreat_name"],
            "payload_json": row["payload_json"],
            "retreat_plan_name": row["retreat_plan_name"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def main() -> int:
    args = parse_args()
    init_db()

    with get_connection() as conn:
        ingredients = fetch_ingredients(conn)
        unit_conversions = fetch_unit_conversions(conn)
        recipes = fetch_recipes(conn)
        vendors = fetch_vendors(conn)
        retreat_plans = fetch_retreat_plans(conn)
        inventory_items = fetch_inventory_items(conn)
        shopping_lists = fetch_shopping_lists(conn)
        service_snapshots = fetch_service_snapshots(conn)

    shopping_list_items_total = sum(len(sl["items"]) for sl in shopping_lists)

    payload = {
        "format": "retreat_ops_master_data",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_db": "backend/data/retreat_ops.db",
        "ingredients": ingredients,
        "unit_conversions": unit_conversions,
        "recipes": recipes,
        "vendors": vendors,
        "retreat_plans": retreat_plans,
        "inventory_items": inventory_items,
        "shopping_lists": shopping_lists,
        "service_snapshots": service_snapshots,
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
        f" vendors={len(vendors)}"
        f" retreat_plans={len(retreat_plans)}"
        f" inventory_items={len(inventory_items)}"
        f" shopping_lists={len(shopping_lists)}"
        f" shopping_list_items={shopping_list_items_total}"
        f" service_snapshots={len(service_snapshots)}"
        f" -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
