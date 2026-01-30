#!/usr/bin/env bash
set -euo pipefail

# DEPRECATED (2026-01): data is now stored in a separate repo under ./data.
# This legacy script previously merged data-sync into the code repo main branch.
# It is intentionally kept to avoid breaking old setups, but should no longer be used.
#
# Usage:
#   ./merge_data_sync_to_main.sh

echo "[ERROR] Deprecated: data repo separated under ./data."
echo "[HINT] Use ./push_data_to_github.sh to push data repo changes instead."
exit 10

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
