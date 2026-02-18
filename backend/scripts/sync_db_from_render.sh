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
REMOTE_EXPORT_PATH="${REMOTE_DIR}/retreat_ops-export-${TIMESTAMP}.db"

mkdir -p "$(dirname "${LOCAL_DB_PATH}")"
if [[ -f "${LOCAL_DB_PATH}" ]]; then
  cp "${LOCAL_DB_PATH}" "${LOCAL_DB_PATH}.bak-${TIMESTAMP}"
  echo "Backed up local DB -> ${LOCAL_DB_PATH}.bak-${TIMESTAMP}"
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
mv "${TMP_LOCAL_PATH}" "${LOCAL_DB_PATH}"

if [[ "${KEEP_REMOTE_EXPORT}" -eq 0 ]]; then
  echo "Cleaning up remote export ${REMOTE_EXPORT_PATH} ..."
  ssh "${SSH_OPTS[@]}" "${TARGET}" "rm -f '${REMOTE_EXPORT_PATH}'"
fi

echo "Sync complete: ${RENDER_REMOTE_DB_PATH} -> ${LOCAL_DB_PATH}"
