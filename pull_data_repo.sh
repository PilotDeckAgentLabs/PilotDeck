#!/usr/bin/env bash
set -euo pipefail

# Pull latest changes for the data repository under ./data.
# This script is intentionally independent from the code repo deploy flow.
#
# Usage:
#   ./pull_data_repo.sh
#
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

echo "[INFO] Data repo: $DATA_DIR"

if git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  echo "[INFO] Remote: $REMOTE_NAME ($(git remote get-url "$REMOTE_NAME"))"
else
  echo "[ERROR] Remote '$REMOTE_NAME' not configured in data repo."
  echo "[HINT] Configure it inside $DATA_DIR (e.g. git remote add $REMOTE_NAME <url>)."
  exit 5
fi

echo "[INFO] Branch: $BRANCH"

# git pull --rebase requires a clean working tree.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[ERROR] Data repo has local changes; cannot pull with rebase."
  echo "[HINT] Commit/stash your data changes in $DATA_DIR, then retry."
  git status --porcelain || true
  exit 2
fi

echo "[INFO] Fetching $REMOTE_NAME..."
git fetch "$REMOTE_NAME" --prune

if git show-ref --verify --quiet "refs/remotes/${REMOTE_NAME}/${BRANCH}"; then
  echo "[INFO] Switching to ${BRANCH} (from ${REMOTE_NAME}/${BRANCH})..."
  git switch -C "${BRANCH}" "${REMOTE_NAME}/${BRANCH}" >/dev/null 2>&1 || git checkout -B "${BRANCH}" "${REMOTE_NAME}/${BRANCH}"
else
  echo "[ERROR] Remote branch not found: ${REMOTE_NAME}/${BRANCH}"
  echo "[HINT] Check your data repo remote/branch settings."
  exit 6
fi

echo "[INFO] Pulling latest..."
git pull --rebase "$REMOTE_NAME" "$BRANCH"

echo "[INFO] Done."
