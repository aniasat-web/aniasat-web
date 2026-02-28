#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_RENDER_SSH_HOST="ssh.oregon.render.com"
DEFAULT_RENDER_SSH_USER="srv-d68mr2a48b3s73aoa59g"
DEFAULT_RENDER_SSH_KEY="${HOME}/.ssh/bitbucket_ed25519"

RENDER_SSH_HOST="${RENDER_SSH_HOST:-${DEFAULT_RENDER_SSH_HOST}}"
RENDER_SSH_USER="${RENDER_SSH_USER:-${DEFAULT_RENDER_SSH_USER}}"
RENDER_SSH_PORT="${RENDER_SSH_PORT:-22}"
RENDER_SSH_KEY="${RENDER_SSH_KEY:-}"
RENDER_REMOTE_DB_PATH="${RENDER_REMOTE_DB_PATH:-/opt/render/project/src/backend/data/retreat_ops.db}"
LOCAL_DB_PATH="${LOCAL_DB_PATH:-${BACKEND_DIR}/data/retreat_ops.db}"
SKIP_REMOTE_BACKUP=0
SYNC_SCOPE="${SYNC_SCOPE:-full}"

usage() {
  cat <<'EOF'
Usage:
  backend/scripts/sync_db_to_render.sh [options]

Options:
  --host HOST            Render SSH host (default: ssh.oregon.render.com)
  --user USER            Render SSH user (default: srv-d68mr2a48b3s73aoa59g)
  --port PORT            Render SSH port (default: 22)
  --key PATH             SSH private key path (default auto-detect: ~/.ssh/bitbucket_ed25519)
  --remote-db PATH       Remote DB path (default: /opt/render/project/src/backend/data/retreat_ops.db)
  --local-db PATH        Local DB path (default: backend/data/retreat_ops.db)
  --scope SCOPE          Sync scope: full (default) or inventory
  --skip-remote-backup   Do not create a remote pre-sync backup
  -h, --help             Show this help

Example:
  backend/scripts/sync_db_to_render.sh \
    --host ssh.oregon.render.com \
    --user srv-xxxxxxxxxxxxxxxxxxxx
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

resolve_python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

if [[ -z "${RENDER_SSH_KEY}" && -f "${DEFAULT_RENDER_SSH_KEY}" ]]; then
  RENDER_SSH_KEY="${DEFAULT_RENDER_SSH_KEY}"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      RENDER_SSH_HOST="${2:-}"
      shift 2
      ;;
    --user)
      RENDER_SSH_USER="${2:-}"
      shift 2
      ;;
    --port)
      RENDER_SSH_PORT="${2:-}"
      shift 2
      ;;
    --key)
      RENDER_SSH_KEY="${2:-}"
      shift 2
      ;;
    --remote-db)
      RENDER_REMOTE_DB_PATH="${2:-}"
      shift 2
      ;;
    --local-db)
      LOCAL_DB_PATH="${2:-}"
      shift 2
      ;;
    --scope)
      SYNC_SCOPE="${2:-}"
      shift 2
      ;;
    --skip-remote-backup)
      SKIP_REMOTE_BACKUP=1
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "${SYNC_SCOPE}" != "full" && "${SYNC_SCOPE}" != "inventory" ]]; then
  echo "Invalid --scope value: ${SYNC_SCOPE}. Expected: full or inventory" >&2
  exit 1
fi

if [[ ! -f "${LOCAL_DB_PATH}" ]]; then
  echo "Local DB not found: ${LOCAL_DB_PATH}" >&2
  exit 1
fi

require_cmd ssh
require_cmd scp
require_cmd date

PY_BIN=""
if [[ "${SYNC_SCOPE}" == "inventory" ]]; then
  PY_BIN="$(resolve_python_bin || true)"
  if [[ -z "${PY_BIN}" ]]; then
    echo "Missing required command for inventory scope: python3 or python" >&2
    exit 1
  fi
fi

if [[ -n "${RENDER_SSH_KEY}" && ! -f "${RENDER_SSH_KEY}" ]]; then
  echo "SSH key not found: ${RENDER_SSH_KEY}" >&2
  exit 1
fi

SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UpdateHostKeys=no -o ServerAliveInterval=30)
SCP_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UpdateHostKeys=no -o ServerAliveInterval=30)

if [[ -n "${RENDER_SSH_PORT}" ]]; then
  SSH_OPTS+=(-p "${RENDER_SSH_PORT}")
  SCP_OPTS+=(-P "${RENDER_SSH_PORT}")
fi
if [[ -n "${RENDER_SSH_KEY}" ]]; then
  SSH_OPTS+=(-i "${RENDER_SSH_KEY}")
  SCP_OPTS+=(-i "${RENDER_SSH_KEY}")
fi

TARGET="${RENDER_SSH_USER}@${RENDER_SSH_HOST}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
REMOTE_DIR="$(dirname "${RENDER_REMOTE_DB_PATH}")"
REMOTE_UPLOAD_PATH="${REMOTE_DIR}/retreat_ops-upload-${TIMESTAMP}.db"
REMOTE_SNAPSHOT_PATH="${REMOTE_DIR}/retreat_ops-snapshot-${TIMESTAMP}.db"
REMOTE_BACKUP_PATH="${RENDER_REMOTE_DB_PATH}.pre-sync-${TIMESTAMP}"

if [[ "${SYNC_SCOPE}" == "full" ]]; then
  echo "Uploading local DB ${LOCAL_DB_PATH} -> ${REMOTE_UPLOAD_PATH} ..."
  scp "${SCP_OPTS[@]}" "${LOCAL_DB_PATH}" "${TARGET}:${REMOTE_UPLOAD_PATH}"
else
  TMP_REMOTE_DB_LOCAL_PATH="${LOCAL_DB_PATH}.remote-${TIMESTAMP}"

  echo "Creating remote SQLite snapshot ${RENDER_REMOTE_DB_PATH} -> ${REMOTE_SNAPSHOT_PATH} ..."
  ssh "${SSH_OPTS[@]}" "${TARGET}" \
    "set -euo pipefail; \
     PY_BIN=\$(command -v python3 || command -v python); \
     \"\${PY_BIN}\" -c \"import sqlite3; src=sqlite3.connect(r'''${RENDER_REMOTE_DB_PATH}'''); dst=sqlite3.connect(r'''${REMOTE_SNAPSHOT_PATH}'''); src.backup(dst); dst.close(); src.close()\""

  echo "Downloading remote snapshot ${REMOTE_SNAPSHOT_PATH} -> ${TMP_REMOTE_DB_LOCAL_PATH} ..."
  scp "${SCP_OPTS[@]}" "${TARGET}:${REMOTE_SNAPSHOT_PATH}" "${TMP_REMOTE_DB_LOCAL_PATH}"
  ssh "${SSH_OPTS[@]}" "${TARGET}" "rm -f '${REMOTE_SNAPSHOT_PATH}'" || true

  echo "Applying inventory-only table overwrite from local DB snapshot ..."
  "${PY_BIN}" - <<PY
import sqlite3
from pathlib import Path

local_db = Path(r'''${LOCAL_DB_PATH}''')
remote_db_local = Path(r'''${TMP_REMOTE_DB_LOCAL_PATH}''')

inventory_tables = [
    "inventory_product_catalog",
    "standalone_inventory",
    "inventory_items",
    "retreat_inventory_categories",
    "retreat_inventory_items",
    "retreat_inventory_locations",
    "retreat_inventory_item_locations",
    "retreat_inventory_levels",
    "retreat_inventory_transactions",
    "retreat_inventory_retreats",
    "retreat_inventory_retreat_requirements",
    "retreat_inventory_purchase_orders",
    "retreat_inventory_purchase_order_items",
]

def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return bool(row)

def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({qident(table)})").fetchall()
    return [str(row[1]) for row in rows]

def create_table_from_local_schema(remote_conn: sqlite3.Connection, local_conn: sqlite3.Connection, table: str) -> bool:
    table_row = local_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    if not table_row or not table_row[0]:
        return False

    remote_conn.execute(str(table_row[0]))

    index_rows = local_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name = ? AND sql IS NOT NULL",
        (table,),
    ).fetchall()
    for index_row in index_rows:
        sql = str(index_row[0] or "").strip()
        if sql:
            remote_conn.execute(sql)
    return True

remote_conn = sqlite3.connect(remote_db_local)
remote_conn.row_factory = sqlite3.Row
local_conn = sqlite3.connect(local_db)
local_conn.row_factory = sqlite3.Row

try:
    remote_conn.execute("PRAGMA foreign_keys = OFF")
    remote_conn.execute("BEGIN")
    for table in inventory_tables:
        if not table_exists(remote_conn, table):
            if table_exists(local_conn, table) and create_table_from_local_schema(remote_conn, local_conn, table):
                print(f"CREATE {table}: created in remote DB from local schema")
            else:
                print(f"SKIP {table}: missing in remote DB and unavailable in local schema")
                continue
        if not table_exists(local_conn, table):
            print(f"SKIP {table}: missing in local DB")
            continue

        remote_cols = table_columns(remote_conn, table)
        local_cols = set(table_columns(local_conn, table))
        common_cols = [col for col in remote_cols if col in local_cols]
        if not common_cols:
            print(f"SKIP {table}: no common columns")
            continue

        cols_sql = ", ".join(qident(col) for col in common_cols)
        placeholders_sql = ", ".join("?" for _ in common_cols)
        rows = local_conn.execute(f"SELECT {cols_sql} FROM {qident(table)}").fetchall()

        remote_conn.execute(f"DELETE FROM {qident(table)}")
        if rows:
            tuples = [tuple(row[col] for col in common_cols) for row in rows]
            remote_conn.executemany(
                f"INSERT INTO {qident(table)} ({cols_sql}) VALUES ({placeholders_sql})",
                tuples,
            )
        print(f"SYNC {table}: {len(rows)} row(s)")

        if "id" in common_cols:
            max_id_row = remote_conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {qident(table)}").fetchone()
            max_id = int(max_id_row[0] or 0)
            seq_exists = remote_conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
            ).fetchone()
            if seq_exists:
                remote_conn.execute(
                    "UPDATE sqlite_sequence SET seq = ? WHERE name = ?",
                    (max_id, table),
                )
                remote_conn.execute(
                    "INSERT INTO sqlite_sequence(name, seq) SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name = ?)",
                    (table, max_id, table),
                )
    remote_conn.commit()
finally:
    try:
        remote_conn.execute("PRAGMA foreign_keys = ON")
    finally:
        local_conn.close()
        remote_conn.close()
PY

  echo "Uploading inventory-merged DB ${TMP_REMOTE_DB_LOCAL_PATH} -> ${REMOTE_UPLOAD_PATH} ..."
  scp "${SCP_OPTS[@]}" "${TMP_REMOTE_DB_LOCAL_PATH}" "${TARGET}:${REMOTE_UPLOAD_PATH}"
  rm -f "${TMP_REMOTE_DB_LOCAL_PATH}"
fi

if [[ "${SKIP_REMOTE_BACKUP}" -eq 0 ]]; then
  echo "Backing up remote DB -> ${REMOTE_BACKUP_PATH} ..."
  ssh "${SSH_OPTS[@]}" "${TARGET}" \
    "set -euo pipefail; \
     if [ -f '${RENDER_REMOTE_DB_PATH}' ]; then \
       PY_BIN=\$(command -v python3 || command -v python); \
       \"\${PY_BIN}\" -c \"import sqlite3; src=sqlite3.connect(r'''${RENDER_REMOTE_DB_PATH}'''); dst=sqlite3.connect(r'''${REMOTE_BACKUP_PATH}'''); src.backup(dst); dst.close(); src.close()\"; \
     fi"
fi

echo "Promoting uploaded DB to ${RENDER_REMOTE_DB_PATH} ..."
ssh "${SSH_OPTS[@]}" "${TARGET}" \
  "set -euo pipefail; \
   mv '${REMOTE_UPLOAD_PATH}' '${RENDER_REMOTE_DB_PATH}'"

echo "Sync complete: ${LOCAL_DB_PATH} -> ${RENDER_REMOTE_DB_PATH}"
if [[ "${SKIP_REMOTE_BACKUP}" -eq 0 ]]; then
  echo "Remote backup available at ${REMOTE_BACKUP_PATH}"
fi
echo "Restart the Render service so all workers pick up the new DB file."
