#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

HOST="${OSRS_BACKEND_HOST:-127.0.0.1}"
PORT="${OSRS_BACKEND_PORT:-8001}"
COUNCIL_WEB_ORIGIN="${COUNCIL_WEB_ORIGIN:-http://localhost:8015}"
LOG_PATH="${OSRS_BACKEND_LOG_PATH:-}"

if [[ -z "${CORS_ALLOWED_ORIGINS:-}" ]]; then
  export CORS_ALLOWED_ORIGINS="http://localhost:8000,${COUNCIL_WEB_ORIGIN},http://127.0.0.1:8015"
fi

if [[ -z "${WEB_SECRET_KEY:-}" ]]; then
  export WEB_SECRET_KEY="dev-secret-key-minimum-32-chars-required-for-production-use"
fi

if [[ -n "${LOG_PATH}" ]]; then
  mkdir -p "$(dirname "${LOG_PATH}")"
  exec >>"${LOG_PATH}" 2>&1
fi

echo "[osrs-runtime] launching web.main:app on ${HOST}:${PORT}"
exec uvicorn web.main:app --host "${HOST}" --port "${PORT}"
