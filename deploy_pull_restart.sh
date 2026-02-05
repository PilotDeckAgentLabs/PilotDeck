#!/usr/bin/env bash
set -euo pipefail

# Ensure HOME is set for non-interactive/systemd environments.
if [[ -z "${HOME:-}" ]]; then
  export HOME="$(eval echo ~$(logname 2>/dev/null || echo root))"
fi

# Pull latest from GitHub and restart service on server.
# Usage:
#   ./deploy_pull_restart.sh
#
# Assumptions:
# - Run on the SERVER (Linux)
# - Repo already cloned
# - Port must be 8689
# - Node.js version matches .nvmrc (enforced below)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pilotdeck"
PORT="8689"

# Required Node.js version (read from .nvmrc)
REQUIRED_NODE_VERSION=""
if [[ -f "$ROOT_DIR/.nvmrc" ]]; then
  REQUIRED_NODE_VERSION=$(cat "$ROOT_DIR/.nvmrc" | tr -d '[:space:]')
fi

echo "[INFO] ===== Deploy diagnostics ====="
echo "[INFO] whoami: $(whoami 2>/dev/null || true)"
echo "[INFO] id: $(id 2>/dev/null || true)"
echo "[INFO] pwd: $(pwd 2>/dev/null || true)"
echo "[INFO] ROOT_DIR: ${ROOT_DIR}"
echo "[INFO] PATH: ${PATH}"
echo "[INFO] SHELL: ${SHELL:-}"
echo "[INFO] HOME: ${HOME:-}"
if [[ -n "$REQUIRED_NODE_VERSION" ]]; then
  echo "[INFO] Required Node.js version: ${REQUIRED_NODE_VERSION}"
fi

# Prefer /usr/local/bin/python3 (user-managed symlink to python3.8+).
# Do NOT repoint /usr/bin/python to avoid breaking system tooling.
PYTHON_BIN=""
if [[ -x "/usr/local/bin/python3" ]]; then
  PYTHON_BIN="/usr/local/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[ERROR] python3 not found. Install Python 3.8+ and ensure 'python3' is on PATH."
  echo "[HINT] Example (no /usr/bin/python changes):"
  echo "       ln -sf /usr/local/bin/python3.8 /usr/local/bin/python3"
  exit 1
fi

echo "[INFO] Python: $(${PYTHON_BIN} -V 2>&1 || true)"

if ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 8) else 1)'; then
  echo "[ERROR] Python 3.8+ required. Found: $(${PYTHON_BIN} -V 2>&1)"
  echo "[HINT] Keep /usr/bin/python untouched; use /usr/local/bin/python3 -> python3.8 symlink instead."
  exit 1
fi

cd "$ROOT_DIR"

echo "[INFO] Repo: $ROOT_DIR"
echo "[INFO] Pulling latest..."

# git pull --rebase requires a clean working tree.
# NOTE: data lives under ./data (ignored by this repo),
# so local runtime data will NOT block code deploys.

# Auto-reset common files that get modified during deployment
# (package-lock.json gets updated by npm ci/install)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[INFO] Working tree has local changes. Checking if auto-reset is safe..."
  
  # Get list of modified files
  MODIFIED_FILES=$(git diff --name-only)
  STAGED_FILES=$(git diff --cached --name-only)
  ALL_CHANGED="$MODIFIED_FILES $STAGED_FILES"
  
  # Files that are safe to auto-reset (modified by build process)
  SAFE_TO_RESET=(
    "frontend/package-lock.json"
  )
  
  # Check if all changes are in the safe list
  AUTO_RESET_OK=1
  for file in $ALL_CHANGED; do
    IS_SAFE=0
    for safe_pattern in "${SAFE_TO_RESET[@]}"; do
      if [[ "$file" == "$safe_pattern" ]]; then
        IS_SAFE=1
        break
      fi
    done
    if [[ $IS_SAFE -eq 0 ]]; then
      AUTO_RESET_OK=0
      break
    fi
  done
  
  if [[ $AUTO_RESET_OK -eq 1 ]]; then
    echo "[INFO] Only build-generated files changed. Auto-resetting..."
    for file in $ALL_CHANGED; do
      echo "[INFO]   Resetting: $file"
      git checkout HEAD -- "$file" 2>/dev/null || true
    done
  else
    echo "[ERROR] Working tree has local changes that cannot be auto-reset."
    echo "[HINT] Please commit or stash your changes, then retry."
    echo ""
    git status --porcelain || true
    exit 2
  fi
fi

git fetch --all --prune
git pull --rebase

# If an existing venv was created with an older Python, rebuild it.
if [[ -d ".venv" ]]; then
  if [[ -x ".venv/bin/python" ]]; then
    if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 8) else 1)'; then
      echo "[WARN] Existing .venv uses an older Python. Rebuilding venv with ${PYTHON_BIN}."
      rm -rf .venv
    fi
  else
    echo "[WARN] Existing .venv is missing bin/python. Rebuilding venv."
    rm -rf .venv
  fi
fi

if [[ ! -d ".venv" ]]; then
  echo "[INFO] Creating venv (.venv)..."
  "${PYTHON_BIN}" -m venv .venv
fi

echo "[INFO] Installing dependencies..."
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Build frontend (required). Try to make npm visible in non-interactive environments
# (e.g., systemd-run) where nvm-managed Node may not be on PATH.
NPM_BIN=""
NODE_BIN=""

# First, try finding npm/node in common system locations
for bin_path in /usr/bin /usr/local/bin /opt/homebrew/bin; do
  if [[ -x "${bin_path}/npm" ]] && [[ -x "${bin_path}/node" ]]; then
    NPM_BIN="${bin_path}/npm"
    NODE_BIN="${bin_path}/node"
    echo "[INFO] Found system Node.js at: ${bin_path}"
    break
  fi
done

# If not found, try loading nvm
  if [[ -z "$NPM_BIN" ]] && ! command -v npm >/dev/null 2>&1; then
    echo "[INFO] npm not found on PATH. Attempting to load nvm..."
    if [[ -z "${HOME:-}" ]]; then
      export HOME="$(eval echo ~$(logname 2>/dev/null || echo root))"
    fi
  
  # Try multiple common nvm locations
  NVM_SEARCH_PATHS=(
    "${NVM_DIR:-}"
    "/root/.nvm"
    "$(eval echo ~$(logname 2>/dev/null || echo root))/.nvm"
  )
  if [[ -n "${HOME:-}" ]]; then
    NVM_SEARCH_PATHS+=("$HOME/.nvm")
  fi
  
  NVM_LOADED=0
  for nvm_path in "${NVM_SEARCH_PATHS[@]}"; do
    if [[ -z "$nvm_path" ]]; then
      continue
    fi
    nvm_script="${nvm_path}/nvm.sh"
    if [[ -s "$nvm_script" ]]; then
      echo "[INFO] Found nvm at: $nvm_script"
      export NVM_DIR="$nvm_path"
      # shellcheck disable=SC1090
      . "$nvm_script"
      # Prefer default, otherwise fall back to any installed node.
      nvm use --silent default >/dev/null 2>&1 || nvm use --silent node >/dev/null 2>&1 || true
      NVM_LOADED=1
      break
    fi
  done
  
  if [[ $NVM_LOADED -eq 0 ]]; then
    echo "[INFO] nvm not found in common locations: ${NVM_SEARCH_PATHS[*]}"
  fi
fi

# Determine which npm/node to use
if [[ -n "$NPM_BIN" ]]; then
  # Use absolute paths we found earlier
  :
elif command -v npm >/dev/null 2>&1; then
  # npm is now on PATH (from nvm or system)
  NPM_BIN="$(command -v npm)"
  NODE_BIN="$(command -v node)"
fi

if [[ -n "$NODE_BIN" ]]; then
  echo "[INFO] Node: $($NODE_BIN -v 2>&1 || true) at $NODE_BIN"
else
  echo "[INFO] Node: (not found)"
fi

if [[ -z "$NPM_BIN" ]]; then
  echo "[ERROR] npm not found. Frontend build is required for the UI."
  echo "[HINT] Install Node.js/npm using one of these methods:"
  echo ""
  echo "  Method 1 (system package - recommended):"
  echo "    # CentOS/RHEL/Alibaba Cloud Linux:"
  echo "    curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -"
  echo "    sudo yum install -y nodejs"
  echo ""
  echo "    # Ubuntu/Debian:"
  echo "    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo bash -"
  echo "    sudo apt-get install -y nodejs"
  echo ""
  echo "  Method 2 (nvm):"
  echo "    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
  echo "    source ~/.bashrc"
  echo "    nvm install --lts"
  echo "    nvm use --lts"
  echo ""
  exit 3
fi

echo "[INFO] npm: $($NPM_BIN -v 2>&1 || true) at $NPM_BIN"

# ===== CRITICAL: Verify Node.js version matches .nvmrc (major version) =====
if [[ -n "$REQUIRED_NODE_VERSION" ]] && [[ -n "$NODE_BIN" ]]; then
  CURRENT_NODE_VERSION=$($NODE_BIN -v 2>&1 || echo "unknown")
  echo "[INFO] Verifying Node.js version..."
  echo "[INFO]   Required: ${REQUIRED_NODE_VERSION}.x (from .nvmrc)"
  echo "[INFO]   Current:  ${CURRENT_NODE_VERSION}"
  
  # Extract major version from current (e.g., v22.22.0 → 22)
  CURRENT_MAJOR=$(echo "$CURRENT_NODE_VERSION" | sed -E 's/^v?([0-9]+)\..*/\1/')
  # Extract major version from required (e.g., 22 or v22 → 22)
  REQUIRED_MAJOR=$(echo "$REQUIRED_NODE_VERSION" | sed -E 's/^v?([0-9]+).*/\1/')
  
  if [[ "$CURRENT_MAJOR" != "$REQUIRED_MAJOR" ]]; then
    echo ""
    echo "[ERROR] ========================================="
    echo "[ERROR] Node.js major version mismatch!"
    echo "[ERROR] ========================================="
    echo "[ERROR] Required: v${REQUIRED_MAJOR}.x (from .nvmrc)"
    echo "[ERROR] Current:  ${CURRENT_NODE_VERSION}"
    echo ""
    echo "[HINT] Install any version from the v${REQUIRED_MAJOR}.x series:"
    echo ""
    echo "  Using nvm (recommended):"
    echo "    nvm install ${REQUIRED_MAJOR}"
    echo "    nvm use ${REQUIRED_MAJOR}"
    echo "    nvm alias default ${REQUIRED_MAJOR}"
    echo ""
    echo "  Or install from NodeSource:"
    echo "    # For CentOS/RHEL:"
    echo "    curl -fsSL https://rpm.nodesource.com/setup_${REQUIRED_MAJOR}.x | sudo bash -"
    echo "    sudo yum install -y nodejs"
    echo ""
    exit 3
  fi
  
  echo "[INFO] ✓ Node.js major version verified: v${CURRENT_MAJOR}.x (${CURRENT_NODE_VERSION})"
  echo "[INFO] ✓ npm version: $($NPM_BIN -v 2>&1 || echo 'unknown')"
fi

echo "[INFO] Building frontend..."
cd "$ROOT_DIR/frontend"

# Force clean dist directory to ensure fresh build
if [[ -d "dist" ]]; then
  echo "[INFO] Removing old dist directory..."
  rm -rf dist
fi

# Always install/update dependencies to ensure consistency
# Use 'npm ci' for clean install (doesn't modify package-lock.json)
echo "[INFO] Installing frontend dependencies (clean install)..."
if ! "$NPM_BIN" ci; then
  echo "[WARN] npm ci failed, falling back to npm install..."
  if ! "$NPM_BIN" install; then
    echo "[ERROR] npm install also failed"
    echo "[ERROR] Aborting deployment. Service will NOT be restarted."
    exit 4
  fi
fi

echo "[INFO] Running production build..."
if ! "$NPM_BIN" run build; then
  echo "[ERROR] npm run build failed"
  echo "[ERROR] Aborting deployment. Service will NOT be restarted."
  exit 4
fi

# Verify build output exists
if [[ ! -d "dist" ]] || [[ ! -f "dist/index.html" ]]; then
  echo "[ERROR] Frontend build failed: dist/index.html not found"
  echo "[ERROR] Aborting deployment. Service will NOT be restarted."
  exit 4
fi

# Verify build artifacts are non-empty
if [[ ! -s "dist/index.html" ]]; then
  echo "[ERROR] Frontend build produced empty index.html"
  echo "[ERROR] Aborting deployment. Service will NOT be restarted."
  exit 4
fi

# Double-check: ensure assets directory exists and has files
if [[ ! -d "dist/assets" ]] || [[ -z "$(ls -A dist/assets 2>/dev/null)" ]]; then
  echo "[ERROR] Frontend build missing assets directory or assets are empty"
  echo "[ERROR] Aborting deployment. Service will NOT be restarted."
  exit 4
fi

# Force touch index.html to ensure latest timestamp (helps with CDN/proxy cache invalidation)
touch dist/index.html

echo "[INFO] Frontend build complete. Output: frontend/dist/"
echo "[INFO] Build artifacts:"
ls -lh dist/ | head -n 10 || true
cd "$ROOT_DIR"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if command -v systemctl >/dev/null 2>&1; then
  if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "[INFO] Installing systemd service: $SERVICE_FILE"
    cat > "$SERVICE_FILE" <<EOF
[Unit]
 Description=PilotDeck (Flask)
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT_DIR
Environment=PM_PORT=$PORT
Environment=PM_DEBUG=0
ExecStart=$ROOT_DIR/.venv/bin/python $ROOT_DIR/server/main.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
  fi

  echo "[INFO] Restarting service..."
  systemctl restart "$SERVICE_NAME"
  systemctl --no-pager --full status "$SERVICE_NAME" | sed -n '1,20p' || true

  # Auto-backup is opt-in.
  echo "[INFO] Auto-backup is not enabled by default."
  echo "[HINT] Enable daily snapshot (+ optional upload): sudo $ROOT_DIR/setup_auto_backup.sh"
  
else
  echo "[WARN] systemctl not found. Falling back to nohup mode."
  PID_FILE="$ROOT_DIR/.server.pid"
  LOG_FILE="$ROOT_DIR/server.log"

  if [[ -f "$PID_FILE" ]]; then
    OLD_PID="$(cat "$PID_FILE" || true)"
    if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
      echo "[INFO] Stopping old process PID=$OLD_PID"
      kill "$OLD_PID" || true
      sleep 1
    fi
  fi

  echo "[INFO] Starting server on port $PORT..."
  (export PM_PORT="$PORT" PM_DEBUG=0; nohup .venv/bin/python server/main.py >> "$LOG_FILE" 2>&1 & echo $! > "$PID_FILE")
  echo "[INFO] Started. PID=$(cat "$PID_FILE")"
fi

echo "[INFO] Done. Open: http://<server-ip>:${PORT}/"
