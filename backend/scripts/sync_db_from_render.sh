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
KEEP_REMOTE_EXPORT=0
SYNC_SCOPE="${SYNC_SCOPE:-full}"

usage() {
  cat <<'EOF'
Usage:
  backend/scripts/sync_db_from_render.sh [options]

Options:
  --host HOST            Render SSH host (default: ssh.oregon.render.com)
  --user USER            Render SSH user (default: srv-d68mr2a48b3s73aoa59g)
  --port PORT            Render SSH port (default: 22)
  --key PATH             SSH private key path (default auto-detect: ~/.ssh/bitbucket_ed25519)
  --remote-db PATH       Remote DB path (default: /opt/render/project/src/backend/data/retreat_ops.db)
  --local-db PATH        Local DB path (default: backend/data/retreat_ops.db)
  --scope SCOPE          Sync scope: full (default) or kitchen
  --keep-remote-export   Keep temporary export file on Render
  -h, --help             Show this help

Example:
  backend/scripts/sync_db_from_render.sh \
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

cleanup_local_sqlite_sidecars() {
  local db_path="$1"
  local wal_path="${db_path}-wal"
  local shm_path="${db_path}-shm"
  local removed=0

  if [[ -f "${wal_path}" || -f "${shm_path}" ]]; then
    rm -f "${wal_path}" "${shm_path}"
    removed=1
  fi

  if [[ "${removed}" -eq 1 ]]; then
    echo "Removed local SQLite sidecars for ${db_path}"
  fi
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
    --keep-remote-export)
      KEEP_REMOTE_EXPORT=1
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

if [[ "${SYNC_SCOPE}" != "full" && "${SYNC_SCOPE}" != "kitchen" ]]; then
  echo "Invalid --scope value: ${SYNC_SCOPE}. Expected: full or kitchen" >&2
  exit 1
fi

require_cmd ssh
require_cmd scp
require_cmd date
PY_BIN="$(resolve_python_bin || true)"
if [[ -z "${PY_BIN}" ]]; then
  echo "Missing required command: python3 or python" >&2
  exit 1
fi

if [[ -n "${RENDER_SSH_KEY}" && ! -f "${RENDER_SSH_KEY}" ]]; then
  echo "SSH key not found: ${RENDER_SSH_KEY}" >&2
  exit 1
fi

SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30)
SCP_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30)

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
REMOTE_EXPORT_PATH="${REMOTE_DIR}/retreat_ops-export-${TIMESTAMP}.db"

mkdir -p "$(dirname "${LOCAL_DB_PATH}")"
if [[ -f "${LOCAL_DB_PATH}" ]]; then
  cp "${LOCAL_DB_PATH}" "${LOCAL_DB_PATH}.bak-${TIMESTAMP}"
  echo "Backed up local DB -> ${LOCAL_DB_PATH}.bak-${TIMESTAMP}"
elif [[ "${SYNC_SCOPE}" == "kitchen" ]]; then
  echo "Local DB not found for kitchen-only sync: ${LOCAL_DB_PATH}" >&2
  exit 1
fi

echo "Creating remote snapshot ${REMOTE_EXPORT_PATH} ..."
ssh "${SSH_OPTS[@]}" "${TARGET}" \
  "set -euo pipefail; \
   test -f '${RENDER_REMOTE_DB_PATH}'; \
   PY_BIN=\$(command -v python3 || command -v python); \
   \"\${PY_BIN}\" -c \"import sqlite3; src=sqlite3.connect(r'''${RENDER_REMOTE_DB_PATH}'''); dst=sqlite3.connect(r'''${REMOTE_EXPORT_PATH}'''); src.backup(dst); dst.close(); src.close()\""

TMP_LOCAL_PATH="${LOCAL_DB_PATH}.download-${TIMESTAMP}"
echo "Downloading remote DB snapshot to ${TMP_LOCAL_PATH} ..."
scp "${SCP_OPTS[@]}" "${TARGET}:${REMOTE_EXPORT_PATH}" "${TMP_LOCAL_PATH}"

if [[ "${SYNC_SCOPE}" == "full" ]]; then
  mv "${TMP_LOCAL_PATH}" "${LOCAL_DB_PATH}"
  cleanup_local_sqlite_sidecars "${LOCAL_DB_PATH}"
  echo "Enforcing SQLite pragmas on local DB ..."
  "${PY_BIN}" -c "import sqlite3; conn=sqlite3.connect(r'''${LOCAL_DB_PATH}'''); conn.execute('PRAGMA journal_mode = WAL'); conn.execute('PRAGMA busy_timeout = 5000'); jm=conn.execute('PRAGMA journal_mode').fetchone()[0]; bt=conn.execute('PRAGMA busy_timeout').fetchone()[0]; conn.close(); print(f'Local DB pragmas: journal_mode={jm}, busy_timeout={bt}')"
else
  echo "Applying kitchen-only table overwrite from remote snapshot ..."
  "${PY_BIN}" - <<PY
import sqlite3
from pathlib import Path

local_db = Path(r'''${LOCAL_DB_PATH}''')
remote_snapshot_db = Path(r'''${TMP_LOCAL_PATH}''')
kitchen_tables = [
    "ingredient_aliases",
    "ingredients",
    "menu_items",
    "recipe_ingredients",
    "recipe_steps",
    "recipes",
    "retreat_plans",
    "retreats",
    "service_snapshots",
    "shopping_list_item_sources",
    "shopping_list_items",
    "shopping_lists",
    "unit_conversions",
    "vendors",
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

local_conn = sqlite3.connect(local_db)
local_conn.row_factory = sqlite3.Row
remote_conn = sqlite3.connect(remote_snapshot_db)
remote_conn.row_factory = sqlite3.Row

try:
    local_conn.execute("PRAGMA foreign_keys = OFF")
    local_conn.execute("BEGIN")

    for table in kitchen_tables:
        if not table_exists(local_conn, table):
            print(f"SKIP {table}: missing in local DB")
            continue
        if not table_exists(remote_conn, table):
            print(f"SKIP {table}: missing in remote snapshot")
            continue

        local_cols = table_columns(local_conn, table)
        remote_cols = set(table_columns(remote_conn, table))
        common_cols = [col for col in local_cols if col in remote_cols]
        if not common_cols:
            print(f"SKIP {table}: no common columns")
            continue

        cols_sql = ", ".join(qident(col) for col in common_cols)
        placeholders_sql = ", ".join("?" for _ in common_cols)
        rows = remote_conn.execute(f"SELECT {cols_sql} FROM {qident(table)}").fetchall()

        local_conn.execute(f"DELETE FROM {qident(table)}")
        if rows:
            tuples = [tuple(row[col] for col in common_cols) for row in rows]
            local_conn.executemany(
                f"INSERT INTO {qident(table)} ({cols_sql}) VALUES ({placeholders_sql})",
                tuples,
            )
        print(f"SYNC {table}: {len(rows)} row(s)")

        if "id" in common_cols:
            max_id_row = local_conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {qident(table)}").fetchone()
            max_id = int(max_id_row[0] or 0)
            seq_exists = local_conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
            ).fetchone()
            if seq_exists:
                local_conn.execute(
                    "UPDATE sqlite_sequence SET seq = ? WHERE name = ?",
                    (max_id, table),
                )
                local_conn.execute(
                    "INSERT INTO sqlite_sequence(name, seq) SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name = ?)",
                    (table, max_id, table),
                )

    local_conn.commit()
finally:
    try:
        local_conn.execute("PRAGMA foreign_keys = ON")
        local_conn.execute("PRAGMA journal_mode = WAL")
        local_conn.execute("PRAGMA busy_timeout = 5000")
        jm = local_conn.execute("PRAGMA journal_mode").fetchone()[0]
        bt = local_conn.execute("PRAGMA busy_timeout").fetchone()[0]
        print(f"Local DB pragmas: journal_mode={jm}, busy_timeout={bt}")
    finally:
        remote_conn.close()
        local_conn.close()
PY
  rm -f "${TMP_LOCAL_PATH}"
fi

if [[ "${KEEP_REMOTE_EXPORT}" -eq 0 ]]; then
  echo "Cleaning up remote export ${REMOTE_EXPORT_PATH} ..."
  ssh "${SSH_OPTS[@]}" "${TARGET}" "rm -f '${REMOTE_EXPORT_PATH}'"
fi

echo "Sync complete: ${RENDER_REMOTE_DB_PATH} -> ${LOCAL_DB_PATH}"
