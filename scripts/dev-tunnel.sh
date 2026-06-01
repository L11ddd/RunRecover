#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WEB_PORT="${RUNRECOVER_WEB_PORT:-5173}"
API_PORT="${RUNRECOVER_API_PORT:-8000}"
TUNNEL_LOG="$(mktemp "${TMPDIR:-/tmp}/runrecover-cloudflared.XXXXXX.log")"

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

"$ROOT_DIR/scripts/dev.sh" &
dev_pid="$!"

echo "Starting Cloudflare tunnel..."
cloudflared tunnel --url "http://127.0.0.1:${WEB_PORT}" --no-autoupdate >"$TUNNEL_LOG" 2>&1 &
tunnel_pid="$!"

public_url=""
for _ in {1..45}; do
  if ! kill -0 "$tunnel_pid" 2>/dev/null; then
    cat "$TUNNEL_LOG" >&2
    exit 1
  fi

  public_url="$(grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' "$TUNNEL_LOG" | tail -n 1 || true)"
  if [[ -n "$public_url" ]]; then
    break
  fi
  sleep 1
done

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
  if ! kill -0 "$dev_pid" 2>/dev/null; then
    wait "$dev_pid"
    exit $?
  fi
  if ! kill -0 "$tunnel_pid" 2>/dev/null; then
    wait "$tunnel_pid"
    exit $?
  fi
  sleep 1
done
