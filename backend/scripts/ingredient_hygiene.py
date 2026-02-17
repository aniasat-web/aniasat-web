#!/usr/bin/env python3
"""Audit and apply safe ingredient/unit hygiene fixes in Retreat Ops DB.

Phase-1 goals:
- Normalize unit spellings/plurals consistently across key tables.
- Auto-fill missing ingredient canonical units when inference is unambiguous.
- Report unresolved ingredients that still need manual decisions.

Usage:
  cd backend
  . .venv/bin/activate
  python scripts/ingredient_hygiene.py                 # dry-run
  python scripts/ingredient_hygiene.py --apply         # write changes
  python scripts/ingredient_hygiene.py --apply --report-json data/ingredient_hygiene_report.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SCRIPT_DIR.parent / "data" / "retreat_ops.db"

MASS_UNITS = {"g", "kg", "lb", "oz"}
VOLUME_UNITS = {"ml", "l", "cup", "tbsp", "tsp"}
COUNT_UNITS = {"piece", "packet", "can", "bunch", "loaf", "sprig", "leaf", "pinch", "bag"}

UNIT_ALIASES = {
    "cups": "cup",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "tbs": "tbsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "gms": "g",
    "gram": "g",
    "grams": "g",
    "kilogram": "kg",
    "kilograms": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "pieces": "piece",
    "packets": "packet",
    "cans": "can",
    "bunches": "bunch",
    "loaves": "loaf",
    "sprigs": "sprig",
    "leaves": "leaf",
    "bags": "bag",
    "pinches": "pinch",
    "cloves": "piece",
    "clove": "piece",
}

UNIT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("recipe_ingredients", "unit"),
    ("ingredients", "canonical_unit"),
    ("inventory_items", "unit"),
    ("shopping_list_items", "required_unit"),
    ("shopping_list_items", "in_stock_unit"),
    ("shopping_list_items", "to_buy_unit"),
    ("unit_conversions", "unit_from"),
    ("unit_conversions", "unit_to"),
)


@dataclass
class RunStats:
    normalized_units: int = 0
    inferred_canonical_units: int = 0
    unresolved_ingredients: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit/apply ingredient unit hygiene fixes.")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite DB (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Default mode is dry-run with rollback.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating DB backup when --apply is used.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path to write detailed JSON report.",
    )
    parser.add_argument(
        "--max-unresolved",
        type=int,
        default=50,
        help="Max unresolved ingredient rows to include in report output preview.",
    )
    return parser.parse_args()


def normalize_unit(raw_unit: str | None) -> str:
    value = str(raw_unit or "").strip().lower()
    if not value:
        return ""
    return UNIT_ALIASES.get(value, value)


def classify_unit(unit: str) -> str:
    if unit in MASS_UNITS:
        return "mass"
    if unit in VOLUME_UNITS:
        return "volume"
    if unit in COUNT_UNITS:
        return "count"
    return "other"


def backup_db(db_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.bak-{timestamp}")
    backup_path.write_bytes(db_path.read_bytes())
    return backup_path


def normalize_units_in_table(cur: sqlite3.Cursor, table: str, col: str) -> int:
    rows = cur.execute(f"SELECT id, {col} AS unit_value FROM {table} WHERE {col} IS NOT NULL").fetchall()
    changed = 0
    for row in rows:
        original = str(row["unit_value"] or "")
        normalized = normalize_unit(original)
        if normalized and normalized != original.strip().lower():
            cur.execute(f"UPDATE {table} SET {col} = ? WHERE id = ?", (normalized, int(row["id"])))
            changed += cur.rowcount
    return changed


def infer_canonical_unit(observed_units: set[str]) -> str | None:
    if not observed_units:
        return None

    classes = {classify_unit(unit) for unit in observed_units}
    if classes == {"mass"}:
        return "g"
    if classes == {"volume"}:
        return "ml"
    if classes == {"count"} and len(observed_units) == 1:
        return next(iter(observed_units))
    if len(observed_units) == 1:
        # Single unknown unit is still a safe canonical placeholder.
        return next(iter(observed_units))
    return None


def infer_missing_canonical_units(cur: sqlite3.Cursor) -> tuple[int, list[dict[str, Any]]]:
    ingredients = cur.execute(
        """
        SELECT id, name, COALESCE(canonical_unit, '') AS canonical_unit
        FROM ingredients
        ORDER BY lower(name)
        """
    ).fetchall()

    updates = 0
    unresolved: list[dict[str, Any]] = []

    for ingredient in ingredients:
        ingredient_id = int(ingredient["id"])
        canonical = normalize_unit(ingredient["canonical_unit"])
        if canonical:
            continue

        unit_rows = cur.execute(
            "SELECT unit FROM recipe_ingredients WHERE ingredient_id = ? AND unit IS NOT NULL",
            (ingredient_id,),
        ).fetchall()
        observed_units = {
            normalize_unit(row["unit"])
            for row in unit_rows
            if normalize_unit(row["unit"])
        }
        inferred = infer_canonical_unit(observed_units)

        if inferred:
            cur.execute("UPDATE ingredients SET canonical_unit = ? WHERE id = ?", (inferred, ingredient_id))
            updates += cur.rowcount
            continue

        unresolved.append(
            {
                "ingredient_id": ingredient_id,
                "ingredient_name": ingredient["name"],
                "observed_units": sorted(observed_units),
                "unit_classes": sorted({classify_unit(unit) for unit in observed_units}),
                "reason": "ambiguous_units" if observed_units else "no_recipe_usage",
            }
        )

    return updates, unresolved


def coverage_stats(cur: sqlite3.Cursor) -> dict[str, int]:
    return {
        "ingredients_total": cur.execute("SELECT COUNT(*) AS c FROM ingredients").fetchone()["c"],
        "ingredients_missing_canonical": cur.execute(
            "SELECT COUNT(*) AS c FROM ingredients WHERE canonical_unit IS NULL OR trim(canonical_unit) = ''"
        ).fetchone()["c"],
        "recipe_rows_total": cur.execute("SELECT COUNT(*) AS c FROM recipe_ingredients").fetchone()["c"],
        "recipe_rows_distinct_units": cur.execute(
            "SELECT COUNT(DISTINCT lower(trim(unit))) AS c FROM recipe_ingredients"
        ).fetchone()["c"],
    }


def build_report(
    cur: sqlite3.Cursor,
    stats: RunStats,
    unresolved: list[dict[str, Any]],
    max_unresolved: int,
) -> dict[str, Any]:
    top_units = [
        {"unit": row["unit"], "count": row["c"]}
        for row in cur.execute(
            """
            SELECT lower(trim(unit)) AS unit, COUNT(*) AS c
            FROM recipe_ingredients
            GROUP BY lower(trim(unit))
            ORDER BY c DESC, unit ASC
            LIMIT 30
            """
        ).fetchall()
    ]

    mixed_ingredients = [
        {
            "ingredient_name": row["ingredient_name"],
            "unit_count": row["unit_count"],
            "units": row["units"].split(",") if row["units"] else [],
        }
        for row in cur.execute(
            """
            SELECT
              i.name AS ingredient_name,
              COUNT(DISTINCT lower(trim(ri.unit))) AS unit_count,
              GROUP_CONCAT(DISTINCT lower(trim(ri.unit))) AS units
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            GROUP BY i.id, i.name
            HAVING COUNT(DISTINCT lower(trim(ri.unit))) >= 2
            ORDER BY unit_count DESC, lower(i.name)
            LIMIT 100
            """
        ).fetchall()
    ]

    return {
        "coverage": coverage_stats(cur),
        "changes": {
            "normalized_units": stats.normalized_units,
            "inferred_canonical_units": stats.inferred_canonical_units,
            "unresolved_ingredients": stats.unresolved_ingredients,
        },
        "top_recipe_units": top_units,
        "ingredients_with_multiple_units": mixed_ingredients,
        "unresolved_ingredients_preview": unresolved[:max_unresolved],
    }


def run(args: argparse.Namespace) -> None:
    db_path = args.db
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    if args.apply and not args.no_backup:
        backup_path = backup_db(db_path)
        print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    stats = RunStats()
    cur.execute("BEGIN")

    for table, col in UNIT_COLUMNS:
        changed = normalize_units_in_table(cur, table, col)
        stats.normalized_units += changed

    inferred_count, unresolved = infer_missing_canonical_units(cur)
    stats.inferred_canonical_units = inferred_count
    stats.unresolved_ingredients = len(unresolved)

    report = build_report(cur, stats, unresolved, args.max_unresolved)

    if args.apply:
        conn.commit()
        mode = "APPLY"
    else:
        conn.rollback()
        mode = "DRY RUN"

    conn.close()

    print(f"\n{mode} summary")
    print(f"- Normalized unit values: {stats.normalized_units}")
    print(f"- Canonical units inferred: {stats.inferred_canonical_units}")
    print(f"- Unresolved ingredients remaining: {stats.unresolved_ingredients}")
    print("- Coverage:")
    print(f"  - Ingredients total: {report['coverage']['ingredients_total']}")
    print(f"  - Missing canonical_unit: {report['coverage']['ingredients_missing_canonical']}")
    print(f"  - Recipe ingredient rows: {report['coverage']['recipe_rows_total']}")
    print(f"  - Distinct recipe units: {report['coverage']['recipe_rows_distinct_units']}")

    if report["unresolved_ingredients_preview"]:
        print("- Unresolved ingredient preview:")
        for row in report["unresolved_ingredients_preview"][:10]:
            units = ", ".join(row["observed_units"]) if row["observed_units"] else "(none)"
            print(f"  - {row['ingredient_name']}: {units} [{row['reason']}]")

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"- JSON report: {args.report_json}")


def main() -> None:
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()

