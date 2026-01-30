#!/usr/bin/env bash
set -euo pipefail

# Push local changes to GitHub (default: only data/projects.json).
# Usage:
#   ./push_data_to_github.sh            # commit+push data/projects.json
#   ./push_data_to_github.sh --all      # commit+push all changes

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DATA_BRANCH="data-sync"

MODE="data-only"
if [[ "${1:-}" == "--all" ]]; then
  MODE="all"
fi

echo "[INFO] Repo: $ROOT_DIR"
echo "[INFO] Mode: $MODE"

echo "[INFO] Fetching origin..."
git fetch origin --prune

if [[ "$MODE" == "data-only" ]]; then
  # Keep data changes on a separate branch to avoid blocking code deploys on main.
  if git show-ref --verify --quiet "refs/remotes/origin/${DATA_BRANCH}"; then
    echo "[INFO] Switching to ${DATA_BRANCH} (from origin/${DATA_BRANCH})..."
    git switch -C "${DATA_BRANCH}" "origin/${DATA_BRANCH}"
  else
    echo "[INFO] Creating ${DATA_BRANCH} (from origin/main)..."
    git switch -C "${DATA_BRANCH}" "origin/main"
  fi
else
  echo "[WARN] Mode=all will push current branch. Use with care."
fi

if [[ "$MODE" == "all" ]]; then
  git add -A
else
  git add data/projects.json
fi

if git diff --cached --quiet; then
  echo "[INFO] Nothing to commit."
  exit 0
fi

MSG="chore(data): sync projects $(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [[ "$MODE" == "all" ]]; then
  MSG="chore: sync changes $(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi

echo "[INFO] Commit..."
git commit -m "$MSG"

echo "[INFO] Push..."

if [[ "$MODE" == "data-only" ]]; then
  git push -u origin "${DATA_BRANCH}"
else
  git push
fi

echo "[INFO] Done."
