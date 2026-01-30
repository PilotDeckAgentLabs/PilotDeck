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
SERVICE_NAME="myprojectmanager"
PORT="8689"

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

if ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 8) else 1)'; then
  echo "[ERROR] Python 3.8+ required. Found: $(${PYTHON_BIN} -V 2>&1)"
  echo "[HINT] Keep /usr/bin/python untouched; use /usr/local/bin/python3 -> python3.8 symlink instead."
  exit 1
fi

cd "$ROOT_DIR"

echo "[INFO] Repo: $ROOT_DIR"
echo "[INFO] Pulling latest..."

# git pull --rebase requires a clean working tree.
# NOTE: data is stored in a separate repo under ./data (ignored by this code repo),
# so data changes will NOT block code deploys.
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

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if command -v systemctl >/dev/null 2>&1; then
  if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "[INFO] Installing systemd service: $SERVICE_FILE"
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=MyProjectManager (Flask)
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT_DIR
Environment=PM_PORT=$PORT
Environment=PM_DEBUG=0
ExecStart=$ROOT_DIR/.venv/bin/python $ROOT_DIR/server/api_server.py
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

  # Setup automatic daily data backup (idempotent)
  echo "[INFO] Setting up automatic daily data backup..."
  BACKUP_SERVICE_FILE="/etc/systemd/system/myprojectmanager-backup.service"
  BACKUP_TIMER_FILE="/etc/systemd/system/myprojectmanager-backup.timer"
  
  # Check if we have write permission to /etc/systemd/system/
  if [[ ! -w "/etc/systemd/system" ]]; then
    echo "[WARN] No write permission to /etc/systemd/system. Skipping automatic backup setup."
    echo "[HINT] Run manually with root: sudo $ROOT_DIR/setup_auto_backup.sh"
  else
    # Install backup service if not exists or if changed
    if [[ ! -f "$BACKUP_SERVICE_FILE" ]] || ! cmp -s "$ROOT_DIR/myprojectmanager-backup.service" "$BACKUP_SERVICE_FILE"; then
      echo "[INFO] Installing backup service: $BACKUP_SERVICE_FILE"
      if cp -f "$ROOT_DIR/myprojectmanager-backup.service" "$BACKUP_SERVICE_FILE" 2>/dev/null; then
        systemctl daemon-reload
      else
        echo "[ERROR] Failed to copy backup service. Need root permission."
      fi
    fi
    
    # Install backup timer if not exists or if changed
    if [[ ! -f "$BACKUP_TIMER_FILE" ]] || ! cmp -s "$ROOT_DIR/myprojectmanager-backup.timer" "$BACKUP_TIMER_FILE"; then
      echo "[INFO] Installing backup timer: $BACKUP_TIMER_FILE"
      if cp -f "$ROOT_DIR/myprojectmanager-backup.timer" "$BACKUP_TIMER_FILE" 2>/dev/null; then
        systemctl daemon-reload
      else
        echo "[ERROR] Failed to copy backup timer. Need root permission."
      fi
    fi
    
    # Enable and start timer (idempotent)
    if ! systemctl is-enabled myprojectmanager-backup.timer >/dev/null 2>&1; then
      echo "[INFO] Enabling backup timer..."
      systemctl enable myprojectmanager-backup.timer 2>/dev/null || echo "[WARN] Failed to enable timer. Need root permission."
    fi
    
    if ! systemctl is-active myprojectmanager-backup.timer >/dev/null 2>&1; then
      echo "[INFO] Starting backup timer..."
      systemctl start myprojectmanager-backup.timer 2>/dev/null || echo "[WARN] Failed to start timer. Need root permission."
    fi
    
    # Show status if timer exists
    if systemctl list-unit-files myprojectmanager-backup.timer >/dev/null 2>&1; then
      echo "[INFO] Backup timer status:"
      systemctl --no-pager status myprojectmanager-backup.timer 2>/dev/null | sed -n '1,10p' || true
      echo "[INFO] Next scheduled backup:"
      systemctl list-timers myprojectmanager-backup.timer --no-pager --no-legend 2>/dev/null || true
    else
      echo "[WARN] Backup timer not installed. Run manually: sudo $ROOT_DIR/setup_auto_backup.sh"
    fi
  fi
  
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
  (export PM_PORT="$PORT" PM_DEBUG=0; nohup .venv/bin/python server/api_server.py >> "$LOG_FILE" 2>&1 & echo $! > "$PID_FILE")
  echo "[INFO] Started. PID=$(cat "$PID_FILE")"
fi

echo "[INFO] Done. Open: http://<server-ip>:${PORT}/"
