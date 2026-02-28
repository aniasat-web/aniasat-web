#!/usr/bin/env python3
"""Import external product UPC catalog rows for inventory barcode lookup.

Primary use case: ingest a WebstaurantStore export into inventory_product_catalog
so /api/inventory/barcode-lookup can resolve store-specific UPCs.

Examples:
  python scripts/import_inventory_product_catalog.py --csv /tmp/webstaurant_upcs.csv
  python scripts/import_inventory_product_catalog.py --csv /tmp/webstaurant_upcs.csv --apply --replace-source
  python scripts/import_inventory_product_catalog.py --csv /tmp/webstaurant_upcs.csv --apply --source webstaurantstore
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SCRIPT_DIR.parent / "data" / "retreat_ops.db"
DEFAULT_SOURCE = "webstaurantstore"
BARCODE_RE = re.compile(r"^\d{8,14}$")

BARCODE_COL_CANDIDATES = ("barcode", "upc", "gtin", "ean", "ean13", "ean_13", "upc_code")
NAME_COL_CANDIDATES = ("product_name", "name", "item_name", "title", "item", "description")
BRAND_COL_CANDIDATES = ("brand", "manufacturer")
CATEGORY_COL_CANDIDATES = ("category", "product_category", "department")
UNIT_COL_CANDIDATES = ("unit", "uom", "pack_unit", "unit_name")
IMAGE_URL_COL_CANDIDATES = ("image_url", "image", "img", "image_link", "thumbnail_url")
PRODUCT_URL_COL_CANDIDATES = ("product_url", "url", "link", "product_link", "webstaurant_url")
SOURCE_SKU_COL_CANDIDATES = ("source_sku", "sku", "item_number", "item_no", "webstaurant_item")
NOTES_COL_CANDIDATES = ("notes", "note", "comments")


@dataclass
class ParsedCatalogRow:
    barcode: str
    product_name: str | None
    brand: str | None
    category: str | None
    unit: str | None
    image_url: str | None
    product_url: str | None
    source_sku: str | None
    notes: str | None
    source: str
    source_row: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import external UPC catalog rows into inventory_product_catalog."
    )
    parser.add_argument("--csv", type=Path, required=True, help="CSV path with UPC/catalog columns")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help=f"SQLite DB path (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help=f"Catalog source label (default: {DEFAULT_SOURCE})")
    parser.add_argument("--barcode-col", default="", help="CSV barcode column (auto-detect if omitted)")
    parser.add_argument("--name-col", default="", help="CSV product name column (auto-detect if omitted)")
    parser.add_argument("--brand-col", default="", help="CSV brand column (auto-detect if omitted)")
    parser.add_argument("--category-col", default="", help="CSV category column (auto-detect if omitted)")
    parser.add_argument("--unit-col", default="", help="CSV unit column (auto-detect if omitted)")
    parser.add_argument("--image-url-col", default="", help="CSV image URL column (auto-detect if omitted)")
    parser.add_argument("--product-url-col", default="", help="CSV product URL column (auto-detect if omitted)")
    parser.add_argument("--source-sku-col", default="", help="CSV source SKU column (auto-detect if omitted)")
    parser.add_argument("--notes-col", default="", help="CSV notes column (auto-detect if omitted)")
    parser.add_argument("--replace-source", action="store_true", help="Delete existing rows for --source before import")
    parser.add_argument("--apply", action="store_true", help="Write to DB (default is dry-run)")
    parser.add_argument("--no-backup", action="store_true", help="Skip DB backup when --apply is used")
    return parser.parse_args()


def normalize_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def normalize_barcode(value: object) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    if not BARCODE_RE.fullmatch(digits):
        return None
    return digits


def backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.bak-{ts}")
    backup_path.write_bytes(db_path.read_bytes())
    return backup_path


def ensure_catalog_table(cur: sqlite3.Cursor) -> None:
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS inventory_product_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            barcode TEXT NOT NULL,
            product_name TEXT,
            brand TEXT,
            category TEXT,
            unit TEXT,
            image_url TEXT,
            product_url TEXT,
            source_sku TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, barcode)
        );
        CREATE INDEX IF NOT EXISTS idx_inventory_product_catalog_barcode ON inventory_product_catalog(barcode);
        CREATE INDEX IF NOT EXISTS idx_inventory_product_catalog_source ON inventory_product_catalog(source);
        CREATE INDEX IF NOT EXISTS idx_inventory_product_catalog_name ON inventory_product_catalog(product_name);
        """
    )


def normalize_header_map(fieldnames: list[str]) -> dict[str, str]:
    return {str(name).strip().lower(): str(name) for name in fieldnames if str(name).strip()}


def resolve_column(
    header_map: dict[str, str],
    explicit_name: str,
    candidates: tuple[str, ...],
    *,
    required: bool = False,
    label: str,
) -> str | None:
    explicit = str(explicit_name or "").strip()
    if explicit:
        key = explicit.lower()
        if key not in header_map:
            raise ValueError(f"Column {explicit!r} for {label} not found in CSV headers.")
        return header_map[key]
    for candidate in candidates:
        if candidate in header_map:
            return header_map[candidate]
    if required:
        raise ValueError(f"Could not auto-detect required {label} column.")
    return None


def read_rows(args: argparse.Namespace) -> tuple[list[ParsedCatalogRow], dict[str, str | None]]:
    if not args.csv.exists():
        raise FileNotFoundError(f"CSV not found: {args.csv}")

    parsed: list[ParsedCatalogRow] = []
    rejected = 0
    dedupe: dict[tuple[str, str], ParsedCatalogRow] = {}
    with args.csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        header_map = normalize_header_map(list(reader.fieldnames))

        barcode_col = resolve_column(
            header_map,
            args.barcode_col,
            BARCODE_COL_CANDIDATES,
            required=True,
            label="barcode",
        )
        name_col = resolve_column(header_map, args.name_col, NAME_COL_CANDIDATES, label="product name")
        brand_col = resolve_column(header_map, args.brand_col, BRAND_COL_CANDIDATES, label="brand")
        category_col = resolve_column(header_map, args.category_col, CATEGORY_COL_CANDIDATES, label="category")
        unit_col = resolve_column(header_map, args.unit_col, UNIT_COL_CANDIDATES, label="unit")
        image_url_col = resolve_column(header_map, args.image_url_col, IMAGE_URL_COL_CANDIDATES, label="image URL")
        product_url_col = resolve_column(header_map, args.product_url_col, PRODUCT_URL_COL_CANDIDATES, label="product URL")
        source_sku_col = resolve_column(header_map, args.source_sku_col, SOURCE_SKU_COL_CANDIDATES, label="source SKU")
        notes_col = resolve_column(header_map, args.notes_col, NOTES_COL_CANDIDATES, label="notes")

        source = str(args.source or DEFAULT_SOURCE).strip().lower() or DEFAULT_SOURCE
        for row_idx, row in enumerate(reader, start=2):
            barcode = normalize_barcode(row.get(barcode_col))
            if not barcode:
                rejected += 1
                continue

            parsed_row = ParsedCatalogRow(
                barcode=barcode,
                product_name=normalize_text(row.get(name_col)) if name_col else None,
                brand=normalize_text(row.get(brand_col)) if brand_col else None,
                category=normalize_text(row.get(category_col)) if category_col else None,
                unit=normalize_text(row.get(unit_col)) if unit_col else None,
                image_url=normalize_text(row.get(image_url_col)) if image_url_col else None,
                product_url=normalize_text(row.get(product_url_col)) if product_url_col else None,
                source_sku=normalize_text(row.get(source_sku_col)) if source_sku_col else None,
                notes=normalize_text(row.get(notes_col)) if notes_col else None,
                source=source,
                source_row=row_idx,
            )
            dedupe[(source, barcode)] = parsed_row

    parsed = list(dedupe.values())
    parsed.sort(key=lambda item: item.barcode)
    selected_cols = {
        "barcode": barcode_col,
        "name": name_col,
        "brand": brand_col,
        "category": category_col,
        "unit": unit_col,
        "image_url": image_url_col,
        "product_url": product_url_col,
        "source_sku": source_sku_col,
        "notes": notes_col,
    }
    print(f"Parsed {len(parsed)} row(s); rejected {rejected} row(s) with invalid barcode.")
    print("Column mapping:")
    for key, value in selected_cols.items():
        print(f"  - {key}: {value or '(none)'}")
    return parsed, selected_cols


def apply_rows(
    cur: sqlite3.Cursor,
    rows: list[ParsedCatalogRow],
    *,
    replace_source: bool,
    source: str,
) -> tuple[int, int]:
    removed = 0
    if replace_source:
        removed = cur.execute("DELETE FROM inventory_product_catalog WHERE lower(source) = lower(?)", (source,)).rowcount

    upserts = 0
    for row in rows:
        cur.execute(
            """
            INSERT INTO inventory_product_catalog(
                source,
                barcode,
                product_name,
                brand,
                category,
                unit,
                image_url,
                product_url,
                source_sku,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(source, barcode) DO UPDATE SET
                product_name = excluded.product_name,
                brand = excluded.brand,
                category = excluded.category,
                unit = excluded.unit,
                image_url = excluded.image_url,
                product_url = excluded.product_url,
                source_sku = excluded.source_sku,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                row.source,
                row.barcode,
                row.product_name,
                row.brand,
                row.category,
                row.unit,
                row.image_url,
                row.product_url,
                row.source_sku,
                row.notes,
            ),
        )
        upserts += 1
    return removed, upserts


def main() -> None:
    args = parse_args()
    rows, _selected_cols = read_rows(args)
    if not rows:
        print("No valid rows to import.")
        return

    if not args.apply:
        print("Dry-run complete. Use --apply to write rows to DB.")
        sample = rows[0]
        print(
            "Sample row:",
            {
                "source": sample.source,
                "barcode": sample.barcode,
                "product_name": sample.product_name,
                "category": sample.category,
                "unit": sample.unit,
                "product_url": sample.product_url,
            },
        )
        return

    if not args.db.exists():
        raise FileNotFoundError(f"DB not found: {args.db}")

    if not args.no_backup:
        backup_path = backup_db(args.db)
        print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        ensure_catalog_table(cur)
        removed, upserts = apply_rows(
            cur,
            rows,
            replace_source=bool(args.replace_source),
            source=str(args.source or DEFAULT_SOURCE).strip().lower() or DEFAULT_SOURCE,
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Import applied. Removed={removed}, upserted={upserts}.")


if __name__ == "__main__":
    main()
