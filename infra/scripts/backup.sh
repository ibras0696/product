#!/usr/bin/env bash
set -euo pipefail

umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/infra/compose.yaml")
BACKUP_ROOT="${BACKUP_ROOT:?Set BACKUP_ROOT to a protected host directory}"
TIMEOUT_SECONDS="${BACKUP_TIMEOUT_SECONDS:-1800}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINATION="$BACKUP_ROOT/$STAMP"
LOCK_DIR="$BACKUP_ROOT/.backup.lock"
IMAGE_TAG_VALUE="${IMAGE_TAG:-local}"
bounded() {
  python3 "$ROOT/infra/scripts/run_with_timeout.py" "$@"
}

case "$TIMEOUT_SECONDS" in
  ''|*[!0-9]*) echo "BACKUP_TIMEOUT_SECONDS must be a positive integer" >&2; exit 2 ;;
esac
if ((TIMEOUT_SECONDS < 1 || TIMEOUT_SECONDS > 86400)); then
  echo "BACKUP_TIMEOUT_SECONDS must be between 1 and 86400" >&2
  exit 2
fi
case "$IMAGE_TAG_VALUE" in
  ''|*[!A-Za-z0-9_.-]*) echo "IMAGE_TAG contains unsupported characters" >&2; exit 2 ;;
esac

mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another backup is already running" >&2
  exit 1
fi
cleanup() {
  rm -rf "$LOCK_DIR"
  if [[ -d "$DESTINATION" && ! -f "$DESTINATION/COMPLETE" ]]; then
    rm -rf "$DESTINATION"
  fi
}
trap cleanup EXIT INT TERM

mkdir "$DESTINATION"

bounded "$TIMEOUT_SECONDS" "${COMPOSE[@]}" exec -T postgres sh -eu -c \
  'pg_dump --format=custom --compress=6 --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  >"$DESTINATION/postgres.dump"

bounded "$TIMEOUT_SECONDS" "${COMPOSE[@]}" run --rm --no-deps -T \
  --entrypoint sh api -eu -c \
  'mkdir -p "$MEDIA_STORAGE_ROOT"; tar -C "$MEDIA_STORAGE_ROOT" -czf - .' \
  >"$DESTINATION/media.tar.gz"

python3 "$ROOT/infra/scripts/checksums.py" create "$DESTINATION/SHA256SUMS" \
  "$DESTINATION/postgres.dump" "$DESTINATION/media.tar.gz"

ALEMBIC_REVISION="$(
  bounded 30 "${COMPOSE[@]}" exec -T postgres sh -eu -c \
    'psql -X -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version_num FROM alembic_version"'
)"
case "$ALEMBIC_REVISION" in
  ''|*[!A-Za-z0-9_.-]*) echo "Unexpected Alembic revision" >&2; exit 1 ;;
esac

cat >"$DESTINATION/metadata.env" <<EOF
created_utc=$STAMP
alembic_revision=$ALEMBIC_REVISION
image_tag=$IMAGE_TAG_VALUE
git_commit=$(git -C "$ROOT" rev-parse --verify HEAD)
EOF
touch "$DESTINATION/COMPLETE"
echo "Backup completed: $DESTINATION"
