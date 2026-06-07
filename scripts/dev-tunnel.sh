#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WEB_PORT="${RUNRECOVER_WEB_PORT:-5173}"
API_PORT="${RUNRECOVER_API_PORT:-8000}"
TUNNEL_LOG="$(mktemp "${TMPDIR:-/tmp}/runrecover-cloudflared.XXXXXX")"

if ! command -v cloudflared >/dev/null 2>&1; then
  cat >&2 <<'EOF'
cloudflared is required for RunRecover tunnel mode.

Install it with:
  brew install cloudflared

Then run:
  npm run dev:tunnel
EOF
  exit 1
fi

dev_pid=""
tunnel_pid=""
tail_pid=""
reuse_existing_dev=""

api_is_ready() {
  command -v curl >/dev/null 2>&1 &&
    curl -fsS "http://127.0.0.1:${API_PORT}/api/health" >/dev/null 2>&1
}

web_is_ready() {
  command -v curl >/dev/null 2>&1 &&
    curl -fsSI "http://127.0.0.1:${WEB_PORT}" >/dev/null 2>&1
}

port_is_listening() {
  local port="$1"

  command -v lsof >/dev/null 2>&1 &&
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

detect_existing_dev() {
  local api_listening=""
  local web_listening=""

  if api_is_ready && web_is_ready; then
    reuse_existing_dev="1"
    return 0
  fi

  if port_is_listening "$API_PORT"; then
    api_listening="1"
  fi
  if port_is_listening "$WEB_PORT"; then
    web_listening="1"
  fi

  if [[ -n "$api_listening" || -n "$web_listening" ]]; then
    cat >&2 <<EOF
Cannot start RunRecover tunnel mode because required ports are already in use.

Expected:
  API: http://127.0.0.1:${API_PORT}/api/health
  Web: http://127.0.0.1:${WEB_PORT}

Stop the existing process using these ports, or start a healthy RunRecover dev
server on both ports before running npm run dev:tunnel again.
EOF
    exit 1
  fi
}

cleanup() {
  if [[ -n "${tail_pid}" ]] && kill -0 "$tail_pid" 2>/dev/null; then
    kill "$tail_pid" 2>/dev/null || true
  fi
  if [[ -n "${tunnel_pid}" ]] && kill -0 "$tunnel_pid" 2>/dev/null; then
    kill "$tunnel_pid" 2>/dev/null || true
  fi
  if [[ -n "${dev_pid}" ]] && kill -0 "$dev_pid" 2>/dev/null; then
    kill "$dev_pid" 2>/dev/null || true
  fi
  rm -f "$TUNNEL_LOG"
}

wait_for_public_url() {
  local public_url=""

  for _ in {1..45}; do
    if ! kill -0 "$tunnel_pid" 2>/dev/null; then
      cat "$TUNNEL_LOG" >&2
      exit 1
    fi

    public_url="$(grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' "$TUNNEL_LOG" | tail -n 1 || true)"
    if [[ -n "$public_url" ]]; then
      printf '%s' "$public_url"
      return 0
    fi
    sleep 1
  done

  return 1
}

trap cleanup EXIT INT TERM

export RUNRECOVER_API_HOST="${RUNRECOVER_API_HOST:-127.0.0.1}"
export RUNRECOVER_API_PORT="$API_PORT"
export RUNRECOVER_WEB_HOST="${RUNRECOVER_WEB_HOST:-127.0.0.1}"
export RUNRECOVER_WEB_PORT="$WEB_PORT"
export RUNRECOVER_CORS_ORIGINS="${RUNRECOVER_CORS_ORIGINS:-http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}}"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-}"
export VITE_PROXY_API_TARGET="${VITE_PROXY_API_TARGET:-http://127.0.0.1:${API_PORT}}"

echo "RunRecover tunnel mode"
echo "  Local URL: http://127.0.0.1:${WEB_PORT}"
echo "  Local API: http://127.0.0.1:${API_PORT}"
echo "  API routing: browser /api requests are proxied by Vite"
echo

detect_existing_dev

if [[ -n "$reuse_existing_dev" ]]; then
  echo "Reusing existing RunRecover dev server on ports ${WEB_PORT} and ${API_PORT}."
else
  "$ROOT_DIR/scripts/dev.sh" &
  dev_pid="$!"
fi

echo "Starting Cloudflare quick tunnel..."
cloudflared tunnel --url "http://127.0.0.1:${WEB_PORT}" --no-autoupdate >"$TUNNEL_LOG" 2>&1 &
tunnel_pid="$!"

public_url="$(wait_for_public_url || true)"
if [[ -n "$public_url" ]]; then
  echo
  echo "RunRecover public tunnel is ready:"
  echo "  Public URL: ${public_url}"
  echo
  echo "Keep this terminal open while other devices use the tunnel."
else
  echo "Cloudflare tunnel started, but no public URL was found yet." >&2
  echo "Recent tunnel log:" >&2
  tail -n 40 "$TUNNEL_LOG" >&2
fi

tail -n +1 -f "$TUNNEL_LOG" &
tail_pid="$!"

while true; do
  if [[ -n "$dev_pid" ]] && ! kill -0 "$dev_pid" 2>/dev/null; then
    wait "$dev_pid"
    exit $?
  fi
  if ! kill -0 "$tunnel_pid" 2>/dev/null; then
    wait "$tunnel_pid"
    exit $?
  fi
  sleep 1
done
