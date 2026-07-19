#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMEOUT_SECONDS="${CERTBOT_TIMEOUT_SECONDS:-900}"
COMPOSE=(docker compose -f "$ROOT/infra/compose.yaml" -f "$ROOT/infra/compose.prod.yaml")
bounded() {
  python3 "$ROOT/infra/scripts/run_with_timeout.py" "$@"
}

case "$TIMEOUT_SECONDS" in
  ''|*[!0-9]*) echo "CERTBOT_TIMEOUT_SECONDS must be a positive integer" >&2; exit 2 ;;
esac
if ((TIMEOUT_SECONDS < 1 || TIMEOUT_SECONDS > 3600)); then
  echo "CERTBOT_TIMEOUT_SECONDS must be between 1 and 3600" >&2
  exit 2
fi

bounded "$TIMEOUT_SECONDS" "${COMPOSE[@]}" --profile tls run --rm certbot-renew
"${COMPOSE[@]}" exec -T gateway nginx -t
"${COMPOSE[@]}" exec -T gateway nginx -s reload
echo "Certificate renewal completed and Nginx reloaded"
