#!/usr/bin/env bash
# Dumps the Postgres database from the running docker-compose stack.
#
# Usage: ./scripts/backup_db.sh [output-dir]
#   (defaults to ./backups; run from the repo root)
set -euo pipefail

cd "$(dirname "$0")/.."

OUT_DIR="${1:-backups}"
mkdir -p "$OUT_DIR"

set -a
# shellcheck disable=SC1091
[ -f .env ] && source .env
set +a

POSTGRES_USER="${POSTGRES_USER:-home_manager}"
POSTGRES_DB="${POSTGRES_DB:-home_manager}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="$OUT_DIR/home_manager_${STAMP}.sql.gz"

docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=plain \
  | gzip > "$OUT_FILE"

echo "Backup written to $OUT_FILE"
