#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
      && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python 3.11+ is required for repository quality checks." >&2
  exit 1
fi

"$PYTHON_BIN" scripts/validate_ai_harness.py
"$PYTHON_BIN" scripts/check_file_sizes.py
"$PYTHON_BIN" scripts/check_python_complexity.py

docker build --target quality -t product-hackathon-backend-quality ./backend

(
  cd frontend
  npm ci
  npm run format:check
  npm run lint
  npm run typecheck
  npm run boundaries
  npm run test:run
  npm run build
)

COMPOSE=(docker compose -f infra/compose.yaml)
docker compose -f infra/compose.yaml config --quiet
docker compose -f infra/compose.yaml -f infra/compose.dev.yaml config --quiet
docker compose -f infra/compose.yaml -f infra/compose.prod.yaml config --quiet

started_stack=0
if ! curl -fsS "http://127.0.0.1:${HTTP_PORT:-8080}/gateway-health" >/dev/null 2>&1; then
  "${COMPOSE[@]}" up -d --build
  started_stack=1
fi
cleanup() {
  if [[ "$started_stack" == "1" ]]; then
    "${COMPOSE[@]}" down
  fi
}
trap cleanup EXIT

for _ in {1..60}; do
  if curl -fsS "http://127.0.0.1:${HTTP_PORT:-8080}/api/health/ready" >/dev/null; then
    break
  fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${HTTP_PORT:-8080}/api/health/ready" >/dev/null

"${COMPOSE[@]}" run --rm api alembic check
(
  cd frontend
  E2E_BASE_URL="http://127.0.0.1:${HTTP_PORT:-8080}" npm run test:e2e
  E2E_BASE_URL="http://127.0.0.1:${HTTP_PORT:-8080}" npm run test:a11y
)

echo "All architecture, test, build, migration, E2E, accessibility, and infrastructure gates passed."
