#!/usr/bin/env bash
set -euo pipefail

# Create a consistent SQLite snapshot (single file) for backups.
#
# Why: In WAL mode, copying pm.db directly may miss uncheckpointed transactions.
# This script uses scripts/sqlite_backup.py (SQLite online backup API).
#
# Usage:
#   ./backup_db_snapshot.sh
#
# Optional env vars:
#   PM_DB_FILE=./data/pm.db
#   PM_BACKUP_FILE=./data/pm_backup.db
#
# Optional cloud upload (opt-in):
#   PM_BACKUP_UPLOAD_URL=https://...            # pre-signed URL or your upload endpoint
#   PM_BACKUP_UPLOAD_TOKEN=...                 # optional bearer token
#   PM_BACKUP_UPLOAD_METHOD=PUT                # PUT (default) or POST

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_FILE="${PM_DB_FILE:-$ROOT_DIR/data/pm.db}"
BACKUP_FILE="${PM_BACKUP_FILE:-$ROOT_DIR/data/pm_backup.db}"

PY=""
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PY="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PY="$(command -v python)"
fi

if [[ -z "$PY" ]]; then
  echo "[ERROR] python not found"
  exit 1
fi

if [[ ! -f "$DB_FILE" ]]; then
  echo "[ERROR] DB file not found: $DB_FILE"
  exit 2
fi

echo "[INFO] DB: $DB_FILE"
echo "[INFO] Backup: $BACKUP_FILE"

"$PY" "$ROOT_DIR/scripts/sqlite_backup.py" --db "$DB_FILE" --out "$BACKUP_FILE"

UPLOAD_URL="${PM_BACKUP_UPLOAD_URL:-}"
if [[ -n "$UPLOAD_URL" ]]; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "[WARN] curl not found; skipping upload."
    echo "[HINT] Install curl, or upload $BACKUP_FILE manually."
  else
    METHOD="${PM_BACKUP_UPLOAD_METHOD:-PUT}"
    TOKEN="${PM_BACKUP_UPLOAD_TOKEN:-}"
    echo "[INFO] Uploading snapshot to: $UPLOAD_URL"

    AUTH_ARGS=()
    if [[ -n "$TOKEN" ]]; then
      AUTH_ARGS=(-H "Authorization: Bearer $TOKEN")
    fi

    # Default behavior: upload file bytes.
    # For most OSS providers, a pre-signed URL + PUT works well.
    curl -fsS -X "$METHOD" "${AUTH_ARGS[@]}" --upload-file "$BACKUP_FILE" "$UPLOAD_URL"
    echo "[INFO] Upload completed."
  fi
fi

echo "[INFO] Done."
