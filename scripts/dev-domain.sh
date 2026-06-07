#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

load_env_file() {
  local file="$1"
  local line key value

  if [[ ! -f "$file" ]]; then
    return 0
  fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line#export }"

    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      if [[ "$value" =~ ^\"(.*)\"$ || "$value" =~ ^\'(.*)\'$ ]]; then
        value="${BASH_REMATCH[1]}"
      fi
      if [[ -z "${!key+x}" ]]; then
        export "$key=$value"
      fi
    fi
  done < "$file"
}

normalize_origin() {
  local url="${1%/}"

  if [[ -z "$url" ]]; then
    return 0
  fi
  if [[ "$url" != http://* && "$url" != https://* ]]; then
    url="https://${url}"
  fi
  if [[ "$url" =~ ^(https?://[^/]+) ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
  else
    printf '%s' "$url"
  fi
}

append_csv_value() {
  local csv="$1"
  local value="$2"

  if [[ -z "$value" ]]; then
    printf '%s' "$csv"
    return 0
  fi
  if [[ ",${csv}," == *",${value},"* ]]; then
    printf '%s' "$csv"
    return 0
  fi
  if [[ -z "$csv" ]]; then
    printf '%s' "$value"
  else
    printf '%s,%s' "$csv" "$value"
  fi
}

load_env_file "$ROOT_DIR/.env.local"
load_env_file "$ROOT_DIR/.env"

WEB_PORT="${RUNRECOVER_WEB_PORT:-5173}"
API_PORT="${RUNRECOVER_API_PORT:-8000}"
PUBLIC_ORIGIN="$(normalize_origin "${RUNRECOVER_PUBLIC_URL:-}")"

export RUNRECOVER_API_HOST="${RUNRECOVER_API_HOST:-127.0.0.1}"
export RUNRECOVER_API_PORT="$API_PORT"
export RUNRECOVER_WEB_HOST="${RUNRECOVER_WEB_HOST:-0.0.0.0}"
export RUNRECOVER_WEB_PORT="$WEB_PORT"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-}"
export VITE_PROXY_API_TARGET="${VITE_PROXY_API_TARGET:-http://127.0.0.1:${API_PORT}}"

DEFAULT_CORS_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"
if [[ -n "$PUBLIC_ORIGIN" ]]; then
  DEFAULT_CORS_ORIGINS="$(append_csv_value "$DEFAULT_CORS_ORIGINS" "$PUBLIC_ORIGIN")"
fi
export RUNRECOVER_CORS_ORIGINS="${RUNRECOVER_CORS_ORIGINS:-$DEFAULT_CORS_ORIGINS}"
if [[ -n "$PUBLIC_ORIGIN" ]]; then
  export RUNRECOVER_CORS_ORIGINS="$(append_csv_value "$RUNRECOVER_CORS_ORIGINS" "$PUBLIC_ORIGIN")"
fi

echo "RunRecover custom-domain mode"
echo "  Local Web: http://127.0.0.1:${WEB_PORT}"
echo "  Local API: http://127.0.0.1:${API_PORT}"
echo "  Web bind host: ${RUNRECOVER_WEB_HOST}"
echo "  API routing: browser /api requests are proxied by Vite"
if [[ -n "$PUBLIC_ORIGIN" ]]; then
  echo "  Public URL: ${PUBLIC_ORIGIN}"
else
  echo "  Public URL: set RUNRECOVER_PUBLIC_URL to print and allow your domain"
fi
echo
echo "This command does not create a public tunnel."
echo "Point your domain, reverse proxy, or port forwarding to this machine's web port."
echo

"$ROOT_DIR/scripts/dev.sh"
