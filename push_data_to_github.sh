#!/usr/bin/env bash
set -euo pipefail

# Push local data repo changes to GitHub (default: only projects.json).
# Usage:
#   ./push_data_to_github.sh            # commit+push data/projects.json (in data repo)
#   ./push_data_to_github.sh --all      # commit+push all changes (in data repo)

# Optional env vars (data repo only):
#   PM_DATA_REMOTE_NAME=origin
#   PM_DATA_BRANCH=main

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$ROOT_DIR/data"

REMOTE_NAME="${PM_DATA_REMOTE_NAME:-origin}"
BRANCH="${PM_DATA_BRANCH:-main}"

if [[ ! -d "$DATA_DIR/.git" ]]; then
  echo "[ERROR] Data repo not found: $DATA_DIR/.git"
  echo "[HINT] Clone your data repository into: $DATA_DIR"
  echo "[HINT] Example: git clone <your-data-repo-url> $DATA_DIR"
  exit 4
fi

cd "$DATA_DIR"

MODE="data-only"
if [[ "${1:-}" == "--all" ]]; then
  MODE="all"
fi

echo "[INFO] Repo: $ROOT_DIR"
echo "[INFO] Data repo: $DATA_DIR"
echo "[INFO] Mode: $MODE"

if git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  echo "[INFO] Remote: $REMOTE_NAME ($(git remote get-url "$REMOTE_NAME"))"
else
  echo "[ERROR] Remote '$REMOTE_NAME' not configured in data repo."
  echo "[HINT] Configure it inside $DATA_DIR (e.g. git remote add $REMOTE_NAME <url>)."
  exit 5
fi

echo "[INFO] Branch: $BRANCH"

echo "[INFO] Fetching $REMOTE_NAME..."
git fetch "$REMOTE_NAME" --prune

if git show-ref --verify --quiet "refs/remotes/${REMOTE_NAME}/${BRANCH}"; then
  echo "[INFO] Switching to ${BRANCH} (from ${REMOTE_NAME}/${BRANCH})..."
  git switch -C "${BRANCH}" "${REMOTE_NAME}/${BRANCH}" >/dev/null 2>&1 || git checkout -B "${BRANCH}" "${REMOTE_NAME}/${BRANCH}"
else
  # First push for this repo/branch.
  echo "[INFO] Creating local branch ${BRANCH}..."
  git switch -c "${BRANCH}" >/dev/null 2>&1 || git checkout -b "${BRANCH}"
fi

if git show-ref --verify --quiet "refs/remotes/${REMOTE_NAME}/${BRANCH}"; then
  echo "[INFO] Rebasing ${BRANCH} onto ${REMOTE_NAME}/${BRANCH}..."
  git pull --rebase "$REMOTE_NAME" "$BRANCH"
fi

if [[ "$MODE" == "all" ]]; then
  git add -A
else
  git add projects.json
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

git push "$REMOTE_NAME" "$BRANCH"

echo "[INFO] Done."
