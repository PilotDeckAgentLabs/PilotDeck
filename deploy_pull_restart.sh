#!/usr/bin/env bash
set -euo pipefail

# Pull latest from GitHub and restart service on server.
# Usage:
#   ./deploy_pull_restart.sh
#
# Assumptions:
# - Run on the SERVER (Linux)
# - Repo already cloned
# - Port must be 8689

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pilotdeck"
PORT="8689"

echo "[INFO] ===== Deploy diagnostics ====="
echo "[INFO] whoami: $(whoami 2>/dev/null || true)"
echo "[INFO] id: $(id 2>/dev/null || true)"
echo "[INFO] pwd: $(pwd 2>/dev/null || true)"
echo "[INFO] ROOT_DIR: ${ROOT_DIR}"
echo "[INFO] PATH: ${PATH}"
echo "[INFO] SHELL: ${SHELL:-}"
echo "[INFO] HOME: ${HOME:-}"

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
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[ERROR] Working tree has local changes; cannot pull with rebase."
  echo "[HINT] Commit/stash your local code changes on the server, then retry."
  git status --porcelain || true
  exit 2
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
if ! command -v npm >/dev/null 2>&1; then
  echo "[INFO] npm not found on PATH. Attempting to load nvm..."
  export NVM_DIR="${NVM_DIR:-${HOME:-/root}/.nvm}"
  if [[ -s "${NVM_DIR}/nvm.sh" ]]; then
    # shellcheck disable=SC1090
    . "${NVM_DIR}/nvm.sh"
    # Prefer default, otherwise fall back to any installed node.
    nvm use --silent default >/dev/null 2>&1 || nvm use --silent node >/dev/null 2>&1 || true
  else
    echo "[INFO] nvm not found at: ${NVM_DIR}/nvm.sh"
  fi
fi

if command -v node >/dev/null 2>&1; then
  echo "[INFO] Node: $(node -v 2>&1 || true)"
else
  echo "[INFO] Node: (not found)"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] npm not found. Frontend build is required for the UI."
  echo "[HINT] Install Node.js/npm or configure nvm so npm is available to this script."
  exit 3
fi

echo "[INFO] npm: $(npm -v 2>&1 || true)"
echo "[INFO] Building frontend..."
cd "$ROOT_DIR/frontend"

# Force clean dist directory to ensure fresh build
if [[ -d "dist" ]]; then
  echo "[INFO] Removing old dist directory..."
  rm -rf dist
fi

# Always install/update dependencies to ensure consistency
echo "[INFO] Installing frontend dependencies..."
if ! npm install; then
  echo "[ERROR] npm install failed"
  echo "[ERROR] Aborting deployment. Service will NOT be restarted."
  exit 4
fi

echo "[INFO] Running production build..."
if ! npm run build; then
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
