from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional dependency in local sqlite mode
    psycopg = None
    dict_row = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "retreat_ops.db"
SCHEMA_SQLITE_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_POSTGRES_PATH = Path(__file__).resolve().parent / "schema_postgres.sql"
MASTER_SEED_PATH = PROJECT_ROOT / "seeds" / "master_data.json"
AUTO_SEED_MASTER_DATA_ENV = "RETREAT_OPS_AUTO_SEED_MASTER_DATA"
AUTO_SEED_DISABLED_VALUES = {"0", "false", "off", "no"}
DATABASE_URL_ENV = "DATABASE_URL"
SQLITE_DB_PATH_ENV = "RETREAT_OPS_SQLITE_DB_PATH"
SQLITE_BUSY_TIMEOUT_MS = 5000

LOGGER = logging.getLogger(__name__)
URL_IN_NOTES_RE = re.compile(r"https?://[^\s|]+", re.IGNORECASE)
IMAGE_URL_SUFFIX_RE = re.compile(r"\.(?:png|jpe?g|webp|gif|bmp|svg)(?:\?.*)?$", re.IGNORECASE)
REFERENCE_URL_LABEL_RE = re.compile(r"^(reference url|image reference)\s*:?\s*$", re.IGNORECASE)
IMPORT_TAG_PREFIX_RE = re.compile(r"^\[import:([^\]]+)\]\s*", re.IGNORECASE)
IMPORT_ROW_TOKEN_RE = re.compile(r"^row=\d+\b", re.IGNORECASE)

DEFAULT_VENDOR_NAMES = [
    "OmProduce",
    "Costco",
    "Sams",
    "Other Indian Store",
    "Shweta Buy from India",
    "Amazon",
    "Webstaurant",
    "Braums",
    "SunriseNatural",
    "Walmart",
    "American grocery store",
]


def _normalize_database_url(raw_url: str) -> str:
    value = str(raw_url or "").strip()
    if value.startswith("postgres://"):
        return "postgresql://" + value[len("postgres://") :]
    return value


def _replace_qmark_placeholders(sql: str) -> str:
    # Keep existing sqlite-style placeholders in code and map them to psycopg's
    # positional placeholder format only when needed.
    if "?" not in sql:
        return sql

    out: list[str] = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    length = len(sql)

    while i < length:
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < length else ""

        if in_line_comment:
            out.append(char)
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            out.append(char)
            if char == "*" and nxt == "/":
                out.append(nxt)
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        if not in_single and not in_double:
            if char == "-" and nxt == "-":
                out.append(char)
                out.append(nxt)
                i += 2
                in_line_comment = True
                continue
            if char == "/" and nxt == "*":
                out.append(char)
                out.append(nxt)
                i += 2
                in_block_comment = True
                continue

        if char == "'" and not in_double:
            out.append(char)
            if in_single and nxt == "'":
                out.append(nxt)
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue

        if char == '"' and not in_single:
            out.append(char)
            in_double = not in_double
            i += 1
            continue

        if char == "?" and not in_single and not in_double:
            out.append("%s")
        else:
            out.append(char)
        i += 1

    return "".join(out)


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    chunk: list[str] = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    length = len(script)

    while i < length:
        char = script[i]
        nxt = script[i + 1] if i + 1 < length else ""

        if in_line_comment:
            chunk.append(char)
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            chunk.append(char)
            if char == "*" and nxt == "/":
                chunk.append(nxt)
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        if not in_single and not in_double:
            if char == "-" and nxt == "-":
                chunk.append(char)
                chunk.append(nxt)
                i += 2
                in_line_comment = True
                continue
            if char == "/" and nxt == "*":
                chunk.append(char)
                chunk.append(nxt)
                i += 2
                in_block_comment = True
                continue

        if char == "'" and not in_double:
            chunk.append(char)
            if in_single and nxt == "'":
                chunk.append(nxt)
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue

        if char == '"' and not in_single:
            chunk.append(char)
            in_double = not in_double
            i += 1
            continue

        if char == ";" and not in_single and not in_double:
            statement = "".join(chunk).strip()
            if statement:
                statements.append(statement)
            chunk = []
            i += 1
            continue

        chunk.append(char)
        i += 1

    trailing = "".join(chunk).strip()
    if trailing:
        statements.append(trailing)
    return statements


class CompatConnection:
    def __init__(self, raw: Any, *, backend: str):
        self._raw = raw
        self.backend = backend

    def execute(self, sql: str, params: Any = None) -> Any:
        if self.backend == "postgres":
            statement = _replace_qmark_placeholders(sql)
            if params is None:
                return self._raw.execute(statement)
            return self._raw.execute(statement, params)
        if params is None:
            return self._raw.execute(sql)
        return self._raw.execute(sql, params)

    def executemany(self, sql: str, params_seq: Any) -> Any:
        if self.backend == "postgres":
            statement = _replace_qmark_placeholders(sql)
            return self._raw.executemany(statement, params_seq)
        return self._raw.executemany(sql, params_seq)

    def executescript(self, script: str) -> None:
        if self.backend == "postgres":
            for statement in _split_sql_statements(script):
                self._raw.execute(statement)
            return
        self._raw.executescript(script)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()

    def __enter__(self) -> "CompatConnection":
        self._raw.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        return self._raw.__exit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)


def get_connection() -> CompatConnection:
    database_url = _normalize_database_url(os.getenv(DATABASE_URL_ENV, ""))
    if database_url:
        if psycopg is None or dict_row is None:
            raise RuntimeError(
                "DATABASE_URL is configured but psycopg is not installed. "
                "Install dependencies from backend/requirements.txt."
            )
        raw = psycopg.connect(database_url, row_factory=dict_row)
        return CompatConnection(raw, backend="postgres")

    sqlite_path_raw = str(os.getenv(SQLITE_DB_PATH_ENV, "") or "").strip()
    sqlite_path = Path(sqlite_path_raw) if sqlite_path_raw else DB_PATH
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(sqlite_path)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    raw.execute("PRAGMA journal_mode = WAL")
    raw.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    return CompatConnection(raw, backend="sqlite")


def table_exists(conn: CompatConnection, table_name: str) -> bool:
    if conn.backend == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
        return bool(row)

    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return bool(row)


def table_columns(conn: CompatConnection, table_name: str) -> set[str]:
    if not table_exists(conn, table_name):
        return set()
    if conn.backend == "postgres":
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table_name,),
        ).fetchall()
        return {str(row["column_name"]).strip() for row in rows}

    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]).strip() for row in rows}


def normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def extract_urls_from_text(raw_text: Any) -> list[str]:
    text = normalize_optional_text(raw_text)
    if not text:
        return []
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_IN_NOTES_RE.findall(text):
        candidate = match.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        urls.append(candidate)
    return urls


def is_image_url(url: str | None) -> bool:
    candidate = normalize_optional_text(url)
    if not candidate:
        return False
    return bool(IMAGE_URL_SUFFIX_RE.search(candidate))


def extract_order_url_and_clean_notes(raw_notes: Any) -> tuple[str | None, str | None, str | None]:
    notes = normalize_optional_text(raw_notes)
    if not notes:
        return None, None, None

    extracted_urls: list[str] = []
    cleaned_parts: list[str] = []
    import_source: str | None = None
    for raw_part in notes.split("|"):
        part = normalize_optional_text(raw_part)
        if not part:
            continue

        import_match = IMPORT_TAG_PREFIX_RE.match(part)
        if import_match:
            extracted_source = normalize_optional_text(import_match.group(1))
            if extracted_source and not import_source:
                import_source = extracted_source
            part = normalize_optional_text(part[import_match.end() :])
            part = normalize_optional_text(IMPORT_ROW_TOKEN_RE.sub("", part or ""))
            if not part:
                continue

        part_urls = extract_urls_from_text(part)
        for url in part_urls:
            if url not in extracted_urls:
                extracted_urls.append(url)

        part_no_urls = URL_IN_NOTES_RE.sub(" ", part)
        part_no_urls = re.sub(r"\s+", " ", part_no_urls).strip()
        part_no_urls = re.sub(r"\s*[:;,.\-]+\s*$", "", part_no_urls).strip()
        if not part_no_urls:
            continue
        if REFERENCE_URL_LABEL_RE.match(part_no_urls):
            continue
        if part_no_urls not in cleaned_parts:
            cleaned_parts.append(part_no_urls)

    order_url: str | None = None
    for url in extracted_urls:
        if not is_image_url(url):
            order_url = url
            break
    if not order_url and extracted_urls:
        order_url = extracted_urls[0]

    cleaned_notes = " | ".join(cleaned_parts) if cleaned_parts else None
    return order_url, cleaned_notes, import_source


def migrate_standalone_inventory_order_urls(conn: CompatConnection) -> None:
    columns = table_columns(conn, "standalone_inventory")
    if not columns:
        return
    if "notes" not in columns or "order_url" not in columns:
        return
    has_import_source = "import_source" in columns

    select_fields = "id, notes, order_url"
    if has_import_source:
        select_fields += ", import_source"
    rows = conn.execute(
        f"SELECT {select_fields} FROM standalone_inventory"
    ).fetchall()
    for row in rows:
        existing_order_url = normalize_optional_text(row["order_url"])
        existing_notes = normalize_optional_text(row["notes"])
        existing_import_source = normalize_optional_text(row["import_source"]) if has_import_source else None
        extracted_order_url, cleaned_notes, extracted_import_source = extract_order_url_and_clean_notes(row["notes"])
        next_order_url = existing_order_url or extracted_order_url
        next_import_source = existing_import_source or extracted_import_source
        if (
            existing_order_url == next_order_url
            and existing_notes == cleaned_notes
            and existing_import_source == next_import_source
        ):
            continue
        if has_import_source:
            conn.execute(
                """
                UPDATE standalone_inventory
                SET notes = ?, order_url = ?, import_source = ?
                WHERE id = ?
                """,
                (cleaned_notes, next_order_url, next_import_source, int(row["id"])),
            )
        else:
            conn.execute(
                """
                UPDATE standalone_inventory
                SET notes = ?, order_url = ?
                WHERE id = ?
                """,
                (cleaned_notes, next_order_url, int(row["id"])),
            )


def ensure_retreat_inventory_location(conn: CompatConnection, location_name: str) -> int:
    clean_name = str(location_name or "").strip()
    if not clean_name:
        raise ValueError("Location name cannot be blank")

    existing = conn.execute(
        """
        SELECT id
        FROM retreat_inventory_locations
        WHERE deleted_at IS NULL
          AND lower(name) = lower(?)
        """,
        (clean_name,),
    ).fetchone()
    if existing:
        return int(existing["id"])

    row = conn.execute(
        """
        INSERT INTO retreat_inventory_locations(
            name,
            active,
            created_at,
            updated_at
        )
        VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        (clean_name,),
    ).fetchone()
    return int(row["id"])


def migrate_retreat_inventory_shelf_locations(conn: CompatConnection) -> None:
    if not table_exists(conn, "retreat_inventory_items"):
        return
    if not table_exists(conn, "retreat_inventory_locations"):
        return
    if not table_exists(conn, "retreat_inventory_item_locations"):
        return

    item_columns = table_columns(conn, "retreat_inventory_items")
    if "shelf_location" not in item_columns:
        return

    rows = conn.execute(
        """
        SELECT
            i.id AS item_id,
            i.shelf_location,
            COALESCE(ril.quantity, 0) AS item_quantity
        FROM retreat_inventory_items i
        LEFT JOIN retreat_inventory_levels ril
          ON ril.item_id = i.id
         AND ril.category_id IS NULL
        WHERE i.deleted_at IS NULL
          AND trim(COALESCE(i.shelf_location, '')) <> ''
        """
    ).fetchall()

    for row in rows:
        item_id = int(row["item_id"])
        location_name = str(row["shelf_location"] or "").strip()
        if not location_name:
            continue

        location_id = ensure_retreat_inventory_location(conn, location_name)
        existing = conn.execute(
            """
            SELECT id
            FROM retreat_inventory_item_locations
            WHERE item_id = ?
              AND location_id = ?
            """,
            (item_id, location_id),
        ).fetchone()
        if existing:
            continue

        quantity = int(row["item_quantity"] or 0)
        if quantity < 0:
            quantity = 0
        conn.execute(
            """
            INSERT INTO retreat_inventory_item_locations(
                item_id,
                location_id,
                quantity,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (item_id, location_id, quantity),
        )


def init_db() -> None:
    with get_connection() as conn:
        schema_path = SCHEMA_POSTGRES_PATH if conn.backend == "postgres" else SCHEMA_SQLITE_PATH
        schema = schema_path.read_text(encoding="utf-8")
        conn.executescript(schema)

        ingredient_columns = table_columns(conn, "ingredients")
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
                WHERE category IN ('Produce', 'Fruits', 'Herbs', 'Dairy & Refrigerated')
                AND purchase_tier IS NULL
                """
            )

        recipe_columns = table_columns(conn, "recipes")
        if "category" not in recipe_columns:
            conn.execute("ALTER TABLE recipes ADD COLUMN category TEXT")

        columns = table_columns(conn, "service_snapshots")
        if "retreat_plan_id" not in columns:
            conn.execute(
                "ALTER TABLE service_snapshots ADD COLUMN retreat_plan_id INTEGER REFERENCES retreat_plans(id) ON DELETE SET NULL"
            )

        shopping_list_columns = table_columns(conn, "shopping_lists")
        if "retreat_plan_id" not in shopping_list_columns:
            conn.execute(
                "ALTER TABLE shopping_lists ADD COLUMN retreat_plan_id INTEGER REFERENCES retreat_plans(id) ON DELETE SET NULL"
            )
        if "phase" not in shopping_list_columns:
            conn.execute("ALTER TABLE shopping_lists ADD COLUMN phase TEXT NOT NULL DEFAULT 'bulk'")

        shopping_item_columns = table_columns(conn, "shopping_list_items")
        if "ordered" not in shopping_item_columns:
            conn.execute("ALTER TABLE shopping_list_items ADD COLUMN ordered INTEGER NOT NULL DEFAULT 0")
        if "ordered_at" not in shopping_item_columns:
            conn.execute("ALTER TABLE shopping_list_items ADD COLUMN ordered_at TEXT")
        if "received" not in shopping_item_columns:
            conn.execute("ALTER TABLE shopping_list_items ADD COLUMN received INTEGER NOT NULL DEFAULT 0")
        if "received_at" not in shopping_item_columns:
            conn.execute("ALTER TABLE shopping_list_items ADD COLUMN received_at TEXT")

        shopping_item_source_columns = table_columns(conn, "shopping_list_item_sources")
        if shopping_item_source_columns and "dish_name" not in shopping_item_source_columns:
            conn.execute("ALTER TABLE shopping_list_item_sources ADD COLUMN dish_name TEXT")

        standalone_inventory_columns = table_columns(conn, "standalone_inventory")
        if standalone_inventory_columns and "barcode" not in standalone_inventory_columns:
            conn.execute("ALTER TABLE standalone_inventory ADD COLUMN barcode TEXT")
        if standalone_inventory_columns and "image_url" not in standalone_inventory_columns:
            conn.execute("ALTER TABLE standalone_inventory ADD COLUMN image_url TEXT")
        if standalone_inventory_columns and "order_url" not in standalone_inventory_columns:
            conn.execute("ALTER TABLE standalone_inventory ADD COLUMN order_url TEXT")
        if standalone_inventory_columns and "import_source" not in standalone_inventory_columns:
            conn.execute("ALTER TABLE standalone_inventory ADD COLUMN import_source TEXT")
        standalone_inventory_columns = table_columns(conn, "standalone_inventory")
        if standalone_inventory_columns and "barcode" in standalone_inventory_columns:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_standalone_inventory_barcode ON standalone_inventory(barcode)")
        if standalone_inventory_columns and "order_url" in standalone_inventory_columns:
            migrate_standalone_inventory_order_urls(conn)
        if standalone_inventory_columns and "category" in standalone_inventory_columns:
            conn.execute(
                """
                UPDATE standalone_inventory
                SET category = 'Infra'
                WHERE category IS NOT NULL
                  AND trim(category) != ''
                  AND lower(trim(category)) IN (
                    'infra',
                    'infrastructure',
                    'maintenance',
                    'facility maintenance',
                    'facilities maintenance',
                    'janitorial',
                    'housekeeping'
                  )
                """
            )

        standalone_order_item_columns = table_columns(conn, "standalone_inventory_order_items")
        if standalone_order_item_columns and "purchase_unit" not in standalone_order_item_columns:
            conn.execute("ALTER TABLE standalone_inventory_order_items ADD COLUMN purchase_unit TEXT NOT NULL DEFAULT 'unit'")
        if standalone_order_item_columns and "units_per_purchase" not in standalone_order_item_columns:
            conn.execute("ALTER TABLE standalone_inventory_order_items ADD COLUMN units_per_purchase REAL NOT NULL DEFAULT 1")
        if standalone_order_item_columns and "ordered_purchase_quantity" not in standalone_order_item_columns:
            conn.execute(
                "ALTER TABLE standalone_inventory_order_items ADD COLUMN ordered_purchase_quantity REAL NOT NULL DEFAULT 0"
            )
        if standalone_order_item_columns and "received_purchase_quantity" not in standalone_order_item_columns:
            conn.execute(
                "ALTER TABLE standalone_inventory_order_items ADD COLUMN received_purchase_quantity REAL NOT NULL DEFAULT 0"
            )
        standalone_order_item_columns = table_columns(conn, "standalone_inventory_order_items")
        if standalone_order_item_columns:
            conn.execute(
                """
                UPDATE standalone_inventory_order_items
                SET purchase_unit = 'unit'
                WHERE purchase_unit IS NULL OR trim(COALESCE(purchase_unit, '')) = ''
                """
            )
            conn.execute(
                """
                UPDATE standalone_inventory_order_items
                SET units_per_purchase = 1
                WHERE units_per_purchase IS NULL OR units_per_purchase <= 0
                """
            )
            conn.execute(
                """
                UPDATE standalone_inventory_order_items
                SET ordered_purchase_quantity = ROUND(
                    ordered_quantity / COALESCE(NULLIF(units_per_purchase, 0), 1),
                    3
                )
                WHERE ordered_quantity > 0
                  AND ordered_purchase_quantity <= 0
                """
            )
            conn.execute(
                """
                UPDATE standalone_inventory_order_items
                SET received_purchase_quantity = ROUND(
                    received_quantity / COALESCE(NULLIF(units_per_purchase, 0), 1),
                    3
                )
                WHERE received_quantity > 0
                  AND received_purchase_quantity <= 0
                """
            )
            conn.execute(
                """
                UPDATE standalone_inventory_order_items
                SET ordered_purchase_quantity = received_purchase_quantity
                WHERE received_purchase_quantity > ordered_purchase_quantity
                """
            )

        retreat_inventory_item_columns = table_columns(conn, "retreat_inventory_items")
        if retreat_inventory_item_columns and "shelf_location" not in retreat_inventory_item_columns:
            conn.execute("ALTER TABLE retreat_inventory_items ADD COLUMN shelf_location TEXT")
        if retreat_inventory_item_columns and "unit" not in retreat_inventory_item_columns:
            conn.execute("ALTER TABLE retreat_inventory_items ADD COLUMN unit TEXT NOT NULL DEFAULT 'each'")
        if retreat_inventory_item_columns and "purchase_url" not in retreat_inventory_item_columns:
            conn.execute("ALTER TABLE retreat_inventory_items ADD COLUMN purchase_url TEXT")
        migrate_retreat_inventory_shelf_locations(conn)

        conn.execute(
            """
            UPDATE shopping_list_items
            SET ordered = 1
            WHERE lower(COALESCE(status, '')) IN ('ordered', 'received') AND ordered = 0
            """
        )
        conn.execute(
            """
            UPDATE shopping_list_items
            SET received = 1, ordered = 1
            WHERE lower(COALESCE(status, '')) = 'received' AND received = 0
            """
        )
        conn.execute(
            """
            UPDATE shopping_list_items
            SET status = CASE
                WHEN received = 1 THEN 'received'
                WHEN ordered = 1 THEN 'ordered'
                ELSE 'open'
            END
            """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_shopping_lists_retreat_plan_id ON shopping_lists(retreat_plan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shopping_items_vendor_id ON shopping_list_items(vendor_id)")
        seed_default_vendors(conn)

        maybe_seed_master_data(conn)
        conn.commit()


def seed_default_vendors(conn: sqlite3.Connection) -> None:
    for name in DEFAULT_VENDOR_NAMES:
        conn.execute(
            """
            INSERT INTO vendors(name)
            SELECT ?
            WHERE NOT EXISTS (
                SELECT 1 FROM vendors WHERE lower(name) = lower(?)
            )
            """,
            (name, name),
        )


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
    counts_str = ", ".join(f"{k}={v}" for k, v in imported.items())
    LOGGER.info("Auto-seeded master data from %s (%s).", MASTER_SEED_PATH, counts_str)


def auto_seed_master_data_enabled() -> bool:
    raw_value = os.getenv(AUTO_SEED_MASTER_DATA_ENV, "1").strip().lower()
    return raw_value not in AUTO_SEED_DISABLED_VALUES


def read_master_data_counts(conn: sqlite3.Connection) -> dict[str, int]:
    # Only check core reference tables — vendors are independently seeded by
    # seed_default_vendors() which runs before this check, so including them
    # would cause the seed to be skipped on a fresh DB.
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

    vendor_count = seed_vendors(conn, payload.get("vendors") or [])
    retreat_plan_count = seed_retreat_plans(conn, payload.get("retreat_plans") or [])
    inventory_count = seed_inventory_items(conn, payload.get("inventory_items") or [])
    shopping_list_count, shopping_item_count = seed_shopping_lists(conn, payload.get("shopping_lists") or [])
    snapshot_count = seed_service_snapshots(conn, payload.get("service_snapshots") or [])

    return {
        "ingredients": ingredient_count,
        "unit_conversions": conversion_count,
        "recipes": recipe_count,
        "vendors": vendor_count,
        "retreat_plans": retreat_plan_count,
        "inventory_items": inventory_count,
        "shopping_lists": shopping_list_count,
        "shopping_list_items": shopping_item_count,
        "service_snapshots": snapshot_count,
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


def seed_vendors(conn: sqlite3.Connection, vendors: list[Any]) -> int:
    count = 0
    for item in vendors:
        if not isinstance(item, dict):
            continue
        name = clean_text(item.get("name"))
        if not name:
            continue
        notes = clean_text(item.get("notes"))
        existing = conn.execute(
            "SELECT id FROM vendors WHERE lower(name) = lower(?)", (name,)
        ).fetchone()
        if existing:
            conn.execute("UPDATE vendors SET notes = ? WHERE id = ?", (notes, existing["id"]))
        else:
            conn.execute("INSERT INTO vendors(name, notes) VALUES (?, ?)", (name, notes))
        count += 1
    return count


def seed_retreat_plans(conn: sqlite3.Connection, plans: list[Any]) -> int:
    count = 0
    for item in plans:
        if not isinstance(item, dict):
            continue
        name = clean_text(item.get("name"))
        if not name:
            continue
        start_date = clean_text(item.get("start_date"))
        day_count = int(item.get("day_count", 1))
        default_people = float(item.get("default_people", 1))
        plan_json = item.get("plan_json", "[]")
        created_at = clean_text(item.get("created_at"))
        updated_at = clean_text(item.get("updated_at"))

        existing = conn.execute(
            "SELECT id FROM retreat_plans WHERE lower(name) = lower(?)", (name,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE retreat_plans
                SET start_date = ?, day_count = ?, default_people = ?,
                    plan_json = ?, created_at = COALESCE(?, created_at),
                    updated_at = COALESCE(?, updated_at)
                WHERE id = ?
                """,
                (start_date, day_count, default_people, plan_json, created_at, updated_at, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO retreat_plans(name, start_date, day_count, default_people, plan_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), COALESCE(?, CURRENT_TIMESTAMP))
                """,
                (name, start_date, day_count, default_people, plan_json, created_at, updated_at),
            )
        count += 1
    return count


def seed_inventory_items(conn: sqlite3.Connection, items: list[Any]) -> int:
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        ingredient_name = clean_text(item.get("ingredient_name"))
        if not ingredient_name:
            continue
        ingredient = conn.execute(
            "SELECT id FROM ingredients WHERE lower(name) = lower(?)", (ingredient_name,)
        ).fetchone()
        if not ingredient:
            LOGGER.warning("Skipping inventory item: ingredient %r not found", ingredient_name)
            continue
        quantity = float(item.get("quantity", 0))
        unit = clean_text(item.get("unit")) or ""
        source = clean_text(item.get("source"))
        updated_at = clean_text(item.get("updated_at"))
        conn.execute(
            """
            INSERT INTO inventory_items(ingredient_id, quantity, unit, source, updated_at)
            VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """,
            (ingredient["id"], quantity, unit, source, updated_at),
        )
        count += 1
    return count


def seed_shopping_lists(conn: sqlite3.Connection, lists: list[Any]) -> tuple[int, int]:
    list_count = 0
    item_count = 0
    for sl in lists:
        if not isinstance(sl, dict):
            continue
        name = clean_text(sl.get("name"))
        if not name:
            continue
        phase = clean_text(sl.get("phase")) or "bulk"
        status = clean_text(sl.get("status")) or "draft"
        created_at = clean_text(sl.get("created_at"))

        retreat_plan_id = None
        retreat_plan_name = clean_text(sl.get("retreat_plan_name"))
        if retreat_plan_name:
            rp = conn.execute(
                "SELECT id FROM retreat_plans WHERE lower(name) = lower(?)", (retreat_plan_name,)
            ).fetchone()
            if rp:
                retreat_plan_id = rp["id"]

        row = conn.execute(
            """
            INSERT INTO shopping_lists(name, phase, status, retreat_plan_id, created_at)
            VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            RETURNING id
            """,
            (name, phase, status, retreat_plan_id, created_at),
        ).fetchone()
        list_id = int(row["id"])
        list_count += 1

        for sli in sl.get("items") or []:
            if not isinstance(sli, dict):
                continue
            ingredient_name = clean_text(sli.get("ingredient_name"))
            if not ingredient_name:
                continue
            ingredient = conn.execute(
                "SELECT id FROM ingredients WHERE lower(name) = lower(?)", (ingredient_name,)
            ).fetchone()
            if not ingredient:
                LOGGER.warning("Skipping shopping list item: ingredient %r not found", ingredient_name)
                continue

            vendor_id = None
            vendor_name = clean_text(sli.get("vendor_name"))
            if vendor_name:
                v = conn.execute(
                    "SELECT id FROM vendors WHERE lower(name) = lower(?)", (vendor_name,)
                ).fetchone()
                if v:
                    vendor_id = v["id"]

            conn.execute(
                """
                INSERT INTO shopping_list_items(
                    shopping_list_id, ingredient_id, required_qty, required_unit,
                    in_stock_qty, in_stock_unit, to_buy_qty, to_buy_unit,
                    vendor_id, owner, pickup_date,
                    ordered, ordered_at, received, received_at,
                    status, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    list_id,
                    ingredient["id"],
                    float(sli.get("required_qty", 0)),
                    clean_text(sli.get("required_unit")) or "",
                    float(sli["in_stock_qty"]) if sli.get("in_stock_qty") is not None else None,
                    clean_text(sli.get("in_stock_unit")),
                    float(sli["to_buy_qty"]) if sli.get("to_buy_qty") is not None else None,
                    clean_text(sli.get("to_buy_unit")),
                    vendor_id,
                    clean_text(sli.get("owner")),
                    clean_text(sli.get("pickup_date")),
                    int(sli.get("ordered", 0)),
                    clean_text(sli.get("ordered_at")),
                    int(sli.get("received", 0)),
                    clean_text(sli.get("received_at")),
                    clean_text(sli.get("status")) or "open",
                    clean_text(sli.get("notes")),
                ),
            )
            item_count += 1

    return list_count, item_count


def seed_service_snapshots(conn: sqlite3.Connection, snapshots: list[Any]) -> int:
    count = 0
    for item in snapshots:
        if not isinstance(item, dict):
            continue
        retreat_name = clean_text(item.get("retreat_name"))
        if not retreat_name:
            continue
        payload_json = item.get("payload_json", "{}")
        created_at = clean_text(item.get("created_at"))

        retreat_plan_id = None
        retreat_plan_name = clean_text(item.get("retreat_plan_name"))
        if retreat_plan_name:
            rp = conn.execute(
                "SELECT id FROM retreat_plans WHERE lower(name) = lower(?)", (retreat_plan_name,)
            ).fetchone()
            if rp:
                retreat_plan_id = rp["id"]

        conn.execute(
            """
            INSERT INTO service_snapshots(retreat_name, payload_json, retreat_plan_id, created_at)
            VALUES (?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """,
            (retreat_name, payload_json, retreat_plan_id, created_at),
        )
        count += 1
    return count
