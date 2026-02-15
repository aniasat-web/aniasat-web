from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "retreat_ops.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


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

        columns = {row[1] for row in conn.execute("PRAGMA table_info(service_snapshots)").fetchall()}
        if "retreat_plan_id" not in columns:
            conn.execute(
                "ALTER TABLE service_snapshots ADD COLUMN retreat_plan_id INTEGER REFERENCES retreat_plans(id) ON DELETE SET NULL"
            )

        conn.commit()
