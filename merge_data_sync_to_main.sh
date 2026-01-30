#!/usr/bin/env bash
set -euo pipefail

# Merge data-sync branch into main and push.
# If merge conflicts occur, the merge is aborted and you must resolve manually.
# Usage:
#   ./merge_data_sync_to_main.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DATA_BRANCH="data-sync"
MAIN_BRANCH="main"

echo "[INFO] Repo: $ROOT_DIR"
echo "[INFO] Fetching origin..."
git fetch origin --prune

if ! git show-ref --verify --quiet "refs/remotes/origin/${DATA_BRANCH}"; then
  echo "[ERROR] origin/${DATA_BRANCH} not found. Push data first."
  exit 4
fi

# Ensure clean working tree.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[ERROR] Working tree has local changes. Refuse to auto-merge."
  echo "[HINT] Commit/stash them, then retry."
  git status --porcelain || true
  exit 2
fi

echo "[INFO] Switching to ${MAIN_BRANCH}..."
git switch "${MAIN_BRANCH}" >/dev/null 2>&1 || git checkout "${MAIN_BRANCH}"

echo "[INFO] Updating ${MAIN_BRANCH} from origin/${MAIN_BRANCH}..."
git pull --rebase origin "${MAIN_BRANCH}"

echo "[INFO] Merging origin/${DATA_BRANCH} -> ${MAIN_BRANCH}..."
set +e
git merge --no-ff --no-commit "origin/${DATA_BRANCH}"
rc=$?
set -e

if [[ $rc -ne 0 ]]; then
  echo "[ERROR] Merge failed (likely conflicts). Auto-merge aborted."
  git merge --abort || true
  echo "[HINT] Please merge manually: git merge origin/${DATA_BRANCH}"
  exit 3
fi

MSG="chore(data): merge ${DATA_BRANCH} into ${MAIN_BRANCH} $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[INFO] Commit merge..."
git commit -m "$MSG"

echo "[INFO] Push ${MAIN_BRANCH}..."
git push origin "${MAIN_BRANCH}"

echo "[INFO] Done."
