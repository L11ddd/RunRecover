#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

API_HOST="${RUNRECOVER_API_HOST:-127.0.0.1}"
API_PORT="${RUNRECOVER_API_PORT:-8000}"
WEB_HOST="${RUNRECOVER_WEB_HOST:-127.0.0.1}"
WEB_PORT="${RUNRECOVER_WEB_PORT:-5173}"
WEB_API_BASE_URL="${VITE_API_BASE_URL:-http://${API_HOST}:${API_PORT}}"

if [[ -x "$API_DIR/.venv/bin/python3" ]]; then
  API_PYTHON="$API_DIR/.venv/bin/python3"
elif [[ -x "$ROOT_DIR/.venv/bin/python3" ]]; then
  API_PYTHON="$ROOT_DIR/.venv/bin/python3"
else
  API_PYTHON="python3"
fi

api_pid=""
web_pid=""

cleanup() {
  if [[ -n "${api_pid}" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
  fi
  if [[ -n "${web_pid}" ]] && kill -0 "$web_pid" 2>/dev/null; then
    kill "$web_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting RunRecover API at http://${API_HOST}:${API_PORT}"
(
  cd "$API_DIR"
  "$API_PYTHON" -m uvicorn app.main:app --reload --host "$API_HOST" --port "$API_PORT"
) &
api_pid="$!"

echo "Starting RunRecover Web at http://${WEB_HOST}:${WEB_PORT}"
(
  cd "$WEB_DIR"
  VITE_API_BASE_URL="$WEB_API_BASE_URL" npm run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
) &
web_pid="$!"

echo
echo "RunRecover is starting:"
echo "  API: http://${API_HOST}:${API_PORT}/api/health"
echo "  Web: http://${WEB_HOST}:${WEB_PORT}"
echo "Press Ctrl+C to stop both services."

while true; do
  if ! kill -0 "$api_pid" 2>/dev/null; then
    wait "$api_pid"
    exit $?
  fi
  if ! kill -0 "$web_pid" 2>/dev/null; then
    wait "$web_pid"
    exit $?
  fi
  sleep 1
done
