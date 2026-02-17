#!/usr/bin/env python3
"""Canonicalize ingredient names/units in the live SQLite DB.

Targets:
- Ingredient names: "Cinnamon stick(s)" -> "Cinnamon", "Ginger paste" -> "Ginger"
- Ginger units in recipe_ingredients: convert all to grams
- Text cleanup in notes/instructions/snapshots: replace legacy phrases

Usage:
  cd backend
  . .venv/bin/activate
  python scripts/canonicalize_ingredients.py          # dry-run (default)
  python scripts/canonicalize_ingredients.py --apply  # write changes
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SCRIPT_DIR.parent / "data" / "retreat_ops.db"

FK_TABLES: tuple[tuple[str, str], ...] = (
    ("recipe_ingredients", "ingredient_id"),
    ("shopping_list_items", "ingredient_id"),
    ("inventory_items", "ingredient_id"),
)

CANONICAL_NAME_GROUPS: dict[str, tuple[str, ...]] = {
    "Cinnamon": ("Cinnamon stick", "Cinnamon sticks"),
    "Ginger": ("Ginger paste",),
}

TEXT_TABLE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("recipe_steps", "instruction"),
    ("recipe_ingredients", "prep_notes"),
    ("recipes", "notes"),
    ("service_snapshots", "payload_json"),
    ("retreat_plans", "plan_json"),
)


@dataclass
class RunStats:
    merged_ingredient_rows: int = 0
    fk_rows_relinked: int = 0
    unit_conversion_rows_renamed: int = 0
    ginger_rows_converted_to_g: int = 0
    ginger_rows_already_g_checked: int = 0
    ginger_rows_unhandled_unit: int = 0
    text_rows_cleaned: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonicalize ingredient naming/units in Retreat Ops DB.")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite DB (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag, runs in dry-run mode and rolls back.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a timestamped backup before apply.",
    )
    return parser.parse_args()


def get_ingredient_id(cur: sqlite3.Cursor, name: str) -> int | None:
    row = cur.execute(
        "SELECT id FROM ingredients WHERE lower(name) = lower(?)",
        (name,),
    ).fetchone()
    return int(row["id"]) if row else None


def ensure_canonical_ingredient(cur: sqlite3.Cursor, canonical: str, aliases: tuple[str, ...]) -> int | None:
    canonical_id = get_ingredient_id(cur, canonical)
    if canonical_id:
        return canonical_id

    for alias in aliases:
        alias_id = get_ingredient_id(cur, alias)
        if alias_id:
            cur.execute("UPDATE ingredients SET name = ? WHERE id = ?", (canonical, alias_id))
            return alias_id
    return None


def merge_alias_into_canonical(cur: sqlite3.Cursor, canonical: str, alias: str, stats: RunStats) -> None:
    canonical_id = ensure_canonical_ingredient(cur, canonical, (alias,))
    if not canonical_id:
        return

    alias_id = get_ingredient_id(cur, alias)
    if not alias_id or alias_id == canonical_id:
        return

    for table, col in FK_TABLES:
        cur.execute(f"UPDATE {table} SET {col} = ? WHERE {col} = ?", (canonical_id, alias_id))
        stats.fk_rows_relinked += cur.rowcount

    cur.execute(
        "UPDATE unit_conversions SET item_name = ? WHERE lower(item_name) = lower(?)",
        (canonical, alias),
    )
    stats.unit_conversion_rows_renamed += cur.rowcount

    cur.execute("DELETE FROM ingredients WHERE id = ?", (alias_id,))
    stats.merged_ingredient_rows += cur.rowcount


def ginger_grams_per_cup(cur: sqlite3.Cursor) -> float:
    row = cur.execute(
        "SELECT grams_per_cup FROM ingredients WHERE lower(name) = lower('Ginger')"
    ).fetchone()
    if row and row["grams_per_cup"]:
        return float(row["grams_per_cup"])
    return 97.0


def ginger_qty_to_grams(quantity: float, unit: str, prep_notes: str, grams_per_cup: float) -> float | None:
    unit_norm = (unit or "").strip().lower()
    qty = float(quantity)
    grams_per_tsp = grams_per_cup / 48.0
    grams_per_tbsp = grams_per_cup / 16.0
    grams_per_inch = 5.0
    grams_per_piece = 5.0

    if unit_norm == "g":
        return qty
    if unit_norm == "kg":
        return qty * 1000.0
    if unit_norm in {"lb", "lbs"}:
        return qty * 453.59237
    if unit_norm == "oz":
        return qty * 28.349523125
    if unit_norm == "cup":
        return qty * grams_per_cup
    if unit_norm == "tbsp":
        return qty * grams_per_tbsp
    if unit_norm == "tsp":
        return qty * grams_per_tsp
    if unit_norm == "inch":
        return qty * grams_per_inch
    if unit_norm in {"piece", "pieces"}:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|\s)?inch", (prep_notes or "").lower())
        if match:
            inches = float(match.group(1))
            return qty * inches * grams_per_inch
        return qty * grams_per_piece
    return None


def convert_ginger_recipe_rows_to_grams(cur: sqlite3.Cursor, stats: RunStats) -> None:
    ginger_id = get_ingredient_id(cur, "Ginger")
    if not ginger_id:
        return

    cur.execute("UPDATE ingredients SET canonical_unit = 'g' WHERE id = ?", (ginger_id,))
    grams_per_cup = ginger_grams_per_cup(cur)

    rows = cur.execute(
        """
        SELECT id, quantity, unit, COALESCE(prep_notes, '') AS prep_notes
        FROM recipe_ingredients
        WHERE ingredient_id = ?
        """,
        (ginger_id,),
    ).fetchall()

    for row in rows:
        converted = ginger_qty_to_grams(
            quantity=float(row["quantity"]),
            unit=row["unit"],
            prep_notes=row["prep_notes"],
            grams_per_cup=grams_per_cup,
        )
        if converted is None:
            stats.ginger_rows_unhandled_unit += 1
            continue

        normalized_qty = round(float(converted), 3)
        if str(row["unit"]).strip().lower() == "g":
            stats.ginger_rows_already_g_checked += 1

        cur.execute(
            "UPDATE recipe_ingredients SET quantity = ?, unit = 'g' WHERE id = ?",
            (normalized_qty, int(row["id"])),
        )
        if cur.rowcount > 0 and str(row["unit"]).strip().lower() != "g":
            stats.ginger_rows_converted_to_g += 1


def cleanup_legacy_text(cur: sqlite3.Cursor, stats: RunStats) -> None:
    for table, col in TEXT_TABLE_COLUMNS:
        rows = cur.execute(f"SELECT id, {col} AS txt FROM {table} WHERE {col} IS NOT NULL").fetchall()
        for row in rows:
            old = row["txt"]
            new = old
            new = re.sub(r"\bcinnamon sticks\b", "cinnamon", new, flags=re.IGNORECASE)
            new = re.sub(r"\bcinnamon stick\b", "cinnamon", new, flags=re.IGNORECASE)
            new = re.sub(r"\bginger paste\b", "ginger", new, flags=re.IGNORECASE)
            if new != old:
                cur.execute(f"UPDATE {table} SET {col} = ? WHERE id = ?", (new, int(row["id"])))
                stats.text_rows_cleaned += cur.rowcount


def run(db_path: Path, apply: bool, make_backup: bool) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    if apply and make_backup:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_name(f"{db_path.name}.bak-{timestamp}")
        backup_path.write_bytes(db_path.read_bytes())
        print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    stats = RunStats()
    cur.execute("BEGIN")

    for canonical, aliases in CANONICAL_NAME_GROUPS.items():
        ensure_canonical_ingredient(cur, canonical, aliases)
        for alias in aliases:
            merge_alias_into_canonical(cur, canonical, alias, stats)

    convert_ginger_recipe_rows_to_grams(cur, stats)
    cleanup_legacy_text(cur, stats)

    checks = {
        "ingredients.cinnamon_sticks": cur.execute(
            "SELECT COUNT(*) AS c FROM ingredients WHERE lower(name) = 'cinnamon sticks'"
        ).fetchone()["c"],
        "ingredients.ginger_paste": cur.execute(
            "SELECT COUNT(*) AS c FROM ingredients WHERE lower(name) = 'ginger paste'"
        ).fetchone()["c"],
        "recipe_steps.ginger_paste_text": cur.execute(
            "SELECT COUNT(*) AS c FROM recipe_steps WHERE lower(instruction) LIKE '%ginger paste%'"
        ).fetchone()["c"],
        "recipe_steps.cinnamon_stick_text": cur.execute(
            "SELECT COUNT(*) AS c FROM recipe_steps WHERE lower(instruction) LIKE '%cinnamon stick%'"
        ).fetchone()["c"],
        "ginger_rows_non_g": cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE lower(i.name) = 'ginger' AND lower(ri.unit) != 'g'
            """
        ).fetchone()["c"],
    }

    if apply:
        conn.commit()
        mode = "APPLY"
    else:
        conn.rollback()
        mode = "DRY RUN"

    conn.close()

    print(f"\n{mode} summary")
    print(f"- Merged ingredient rows: {stats.merged_ingredient_rows}")
    print(f"- FK relinks: {stats.fk_rows_relinked}")
    print(f"- unit_conversions item_name renames: {stats.unit_conversion_rows_renamed}")
    print(f"- Ginger rows converted to grams: {stats.ginger_rows_converted_to_g}")
    print(f"- Ginger rows already in grams checked: {stats.ginger_rows_already_g_checked}")
    print(f"- Ginger rows with unhandled units: {stats.ginger_rows_unhandled_unit}")
    print(f"- Text rows cleaned: {stats.text_rows_cleaned}")
    print("- Post-checks:")
    for key, value in checks.items():
        print(f"  - {key}: {value}")


def main() -> None:
    args = parse_args()
    run(db_path=args.db, apply=args.apply, make_backup=not args.no_backup)


if __name__ == "__main__":
    main()
