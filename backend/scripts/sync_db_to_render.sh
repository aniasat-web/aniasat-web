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

if [[ ! -f "${LOCAL_DB_PATH}" ]]; then
  echo "Local DB not found: ${LOCAL_DB_PATH}" >&2
  exit 1
fi

require_cmd ssh
require_cmd scp
require_cmd date

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
REMOTE_UPLOAD_PATH="${REMOTE_DIR}/retreat_ops-upload-${TIMESTAMP}.db"
REMOTE_BACKUP_PATH="${RENDER_REMOTE_DB_PATH}.pre-sync-${TIMESTAMP}"

echo "Uploading local DB ${LOCAL_DB_PATH} -> ${REMOTE_UPLOAD_PATH} ..."
scp "${SCP_OPTS[@]}" "${LOCAL_DB_PATH}" "${TARGET}:${REMOTE_UPLOAD_PATH}"

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
