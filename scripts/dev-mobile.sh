#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [[ -z "$LAN_IP" ]]; then
  LAN_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi

if [[ -z "$LAN_IP" ]]; then
  echo "Unable to detect a LAN IP address." >&2
  echo "Connect this Mac to Wi-Fi, then retry. Checked: ipconfig getifaddr en0, en1." >&2
  exit 1
fi

export RUNRECOVER_API_HOST="0.0.0.0"
export RUNRECOVER_API_PORT="8000"
export RUNRECOVER_WEB_HOST="0.0.0.0"
export RUNRECOVER_WEB_PORT="5173"
export RUNRECOVER_LAN_IP="$LAN_IP"
export VITE_API_BASE_URL="http://${LAN_IP}:8000"
export VITE_PROXY_API_TARGET="http://${LAN_IP}:8000"
export RUNRECOVER_CORS_ORIGINS="http://${LAN_IP}:5173,http://127.0.0.1:5173,http://localhost:5173"

echo "RunRecover mobile LAN mode"
echo "  Mac local URL:    http://127.0.0.1:5173"
echo "  Phone Wi-Fi URL:  http://${LAN_IP}:5173"
echo "  API URL:          http://${LAN_IP}:8000"
echo
echo "Make sure your phone and Mac are on the same Wi-Fi network."
echo

exec "$ROOT_DIR/scripts/dev.sh"
