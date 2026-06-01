#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

detect_lan_ip() {
  local ip

  ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "$ip" ]]; then
    ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  if [[ -z "$ip" ]] && command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  fi

  printf '%s' "$ip"
}

LAN_IP="${RUNRECOVER_LAN_IP:-$(detect_lan_ip)}"

API_HOST="${RUNRECOVER_API_HOST:-127.0.0.1}"
API_PORT="${RUNRECOVER_API_PORT:-8000}"
WEB_HOST="${RUNRECOVER_WEB_HOST:-127.0.0.1}"
WEB_PORT="${RUNRECOVER_WEB_PORT:-5173}"
API_PROXY_TARGET="${VITE_PROXY_API_TARGET:-http://127.0.0.1:${API_PORT}}"
WEB_API_BASE_URL="${VITE_API_BASE_URL:-}"

if [[ -z "${RUNRECOVER_CORS_ORIGINS:-}" ]]; then
  if [[ -n "$LAN_IP" ]]; then
    export RUNRECOVER_CORS_ORIGINS="http://${LAN_IP}:${WEB_PORT},http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"
  else
    export RUNRECOVER_CORS_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"
  fi
fi

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
  VITE_API_BASE_URL="$WEB_API_BASE_URL" VITE_PROXY_API_TARGET="$API_PROXY_TARGET" npm run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
) &
web_pid="$!"

echo
echo "RunRecover is starting:"
echo "  API: http://${API_HOST}:${API_PORT}/api/health"
echo "  Web: http://${WEB_HOST}:${WEB_PORT}"
if [[ -n "$LAN_IP" ]]; then
  echo "  Local URL: http://127.0.0.1:${WEB_PORT}"
  echo "  LAN URL:   http://${LAN_IP}:${WEB_PORT}"
fi
echo "  Browser API path: /api"
echo "  Vite API proxy:   ${API_PROXY_TARGET}"
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
