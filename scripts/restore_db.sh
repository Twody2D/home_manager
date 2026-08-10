#!/usr/bin/env bash
# Restores a Postgres backup produced by backup_db.sh into the running
# docker-compose stack. DESTRUCTIVE: drops and recreates the target database.
#
# Usage: ./scripts/restore_db.sh backups/home_manager_20260810T120000Z.sql.gz
set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_FILE="${1:?Usage: restore_db.sh <backup-file.sql.gz>}"
[ -f "$BACKUP_FILE" ] || { echo "No such file: $BACKUP_FILE" >&2; exit 1; }

set -a
# shellcheck disable=SC1091
[ -f .env ] && source .env
set +a

POSTGRES_USER="${POSTGRES_USER:-home_manager}"
POSTGRES_DB="${POSTGRES_DB:-home_manager}"

read -r -p "This will DROP and recreate database '$POSTGRES_DB'. Continue? [y/N] " CONFIRM
[ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ] || { echo "Aborted."; exit 1; }

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";" \
  -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";"

gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Restored $BACKUP_FILE into database '$POSTGRES_DB'."
