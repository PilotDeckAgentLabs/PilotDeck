#!/usr/bin/env bash
set -euo pipefail

# DEPRECATED.
#
# This project no longer manages ./data via a git repository.
# Future backups may upload snapshots to object storage.
#
# Use instead:
#   ./backup_db_snapshot.sh

echo "[ERROR] Deprecated: push_data_to_github.sh is removed (data dir is not git-managed)."
echo "[HINT] Create a local SQLite snapshot: ./backup_db_snapshot.sh"
echo "[HINT] Then upload data/pm_backup.db to your backup storage (manual for now)."
exit 2
