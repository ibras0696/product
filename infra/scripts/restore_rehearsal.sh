#!/usr/bin/env bash
set -euo pipefail

umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_SET="${BACKUP_SET:?Set BACKUP_SET to a completed backup directory}"
RESTORE_PROJECT="${RESTORE_PROJECT:-product_restore_$(date -u +%Y%m%d%H%M%S)}"
TIMEOUT_SECONDS="${RESTORE_TIMEOUT_SECONDS:-1800}"
MAX_MEDIA_BYTES="${MAX_MEDIA_RESTORE_BYTES:-53687091200}"
KEEP_RESTORE="${KEEP_RESTORE:-0}"
COMPOSE=(docker compose -p "$RESTORE_PROJECT" -f "$ROOT/infra/compose.yaml")
bounded() {
  python3 "$ROOT/infra/scripts/run_with_timeout.py" "$@"
}

case "$RESTORE_PROJECT" in
  product_restore_[A-Za-z0-9_-]*) ;;
  *) echo "RESTORE_PROJECT must start with product_restore_" >&2; exit 2 ;;
esac
for value in "$TIMEOUT_SECONDS" "$MAX_MEDIA_BYTES"; do
  case "$value" in
    ''|*[!0-9]*) echo "Restore limits must be positive integers" >&2; exit 2 ;;
  esac
done
if ((TIMEOUT_SECONDS < 1 || TIMEOUT_SECONDS > 86400 || MAX_MEDIA_BYTES < 1)); then
  echo "Restore limits are outside accepted bounds" >&2
  exit 2
fi
for file in COMPLETE SHA256SUMS postgres.dump media.tar.gz metadata.env; do
  test -f "$BACKUP_SET/$file" || { echo "Backup set is incomplete" >&2; exit 1; }
done

cleanup() {
  rm -f "${RECORDS_FILE:-}"
  if [[ "$KEEP_RESTORE" != "1" ]]; then
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

bounded 60 python3 "$ROOT/infra/scripts/checksums.py" verify "$BACKUP_SET/SHA256SUMS"

"${COMPOSE[@]}" up -d postgres
for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T postgres sh -eu -c \
    'pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
bounded 30 "${COMPOSE[@]}" exec -T postgres sh -eu -c \
  'pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null

bounded "$TIMEOUT_SECONDS" "${COMPOSE[@]}" exec -T postgres sh -eu -c \
  'pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  <"$BACKUP_SET/postgres.dump"

RECORDS_FILE="$(mktemp)"
bounded 60 "${COMPOSE[@]}" exec -T postgres sh -eu -c \
  'psql -X -qAt -F "\t" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    SELECT '\''submission'\'', checksum, original_storage_key, preview_storage_key
      FROM media_submission_assets
    UNION ALL
    SELECT '\''published'\'', '\'''\'', storage_key, '\'''\''
      FROM media_assets
    ORDER BY 1, 3"' >"$RECORDS_FILE"

bounded "$TIMEOUT_SECONDS" "${COMPOSE[@]}" run --rm --no-deps -T \
  -v "$BACKUP_SET:/restore:ro" \
  -v "$ROOT/infra/scripts/restore_media.py:/restore_media.py:ro" \
  --entrypoint python api /restore_media.py \
  --archive /restore/media.tar.gz \
  --root /home/appuser/media \
  --max-bytes "$MAX_MEDIA_BYTES" <"$RECORDS_FILE"

bounded 60 "${COMPOSE[@]}" exec -T postgres sh -eu -c \
  'psql -X -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    SELECT CASE
      WHEN EXISTS (SELECT 1 FROM alembic_version)
       AND EXISTS (SELECT 1 FROM pg_extension WHERE extname = '\''postgis'\'')
      THEN '\''restore_ok'\'' ELSE '\''restore_failed'\'' END"' \
  | grep -qx restore_ok

echo "Isolated restore rehearsal passed for project $RESTORE_PROJECT"
