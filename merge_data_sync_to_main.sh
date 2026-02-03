#!/usr/bin/env bash
set -euo pipefail

# DEPRECATED.
#
# This project no longer manages ./data via a git repository, and no longer merges
# data branches into the code repository.

echo "[ERROR] Deprecated: merge_data_sync_to_main.sh is removed."
echo "[HINT] Use ./backup_db_snapshot.sh to create a SQLite snapshot instead."
exit 2
