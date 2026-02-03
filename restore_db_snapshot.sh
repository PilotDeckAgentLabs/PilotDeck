#!/usr/bin/env bash
set -euo pipefail

# Restore SQLite DB from a snapshot file.
#
# WARNING: This overwrites the live DB file. Stop the service first.
#
# Usage:
#   ./restore_db_snapshot.sh --from ./data/pm_backup.db --force
#
# Optional env vars:
#   PM_DB_FILE=./data/pm.db

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_FILE="${PM_DB_FILE:-$ROOT_DIR/data/pm.db}"
FROM=""
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from)
      FROM="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    *)
      echo "Usage: $0 --from <snapshot.db> --force"
      exit 2
      ;;
  esac
done

if [[ -z "$FROM" ]]; then
  echo "[ERROR] --from is required"
  exit 2
fi

if [[ ! -f "$FROM" ]]; then
  echo "[ERROR] Snapshot not found: $FROM"
  exit 2
fi

if [[ "$FORCE" -ne 1 ]]; then
  echo "[ERROR] Refusing to overwrite without --force"
  echo "[HINT] Stop the service, then run: $0 --from $FROM --force"
  exit 3
fi

mkdir -p "$(dirname "$DB_FILE")"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -f "$DB_FILE" ]]; then
  echo "[INFO] Backing up current DB to: ${DB_FILE}.bak.${TS}"
  cp -f "$DB_FILE" "${DB_FILE}.bak.${TS}"
fi

echo "[INFO] Restoring snapshot -> $DB_FILE"
cp -f "$FROM" "$DB_FILE"

echo "[INFO] Done. Restart the service."
