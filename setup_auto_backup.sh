#!/usr/bin/env bash
set -euo pipefail

# Setup automatic daily SQLite snapshot using systemd timer
# This script installs pilotdeck-backup.{service,timer} to systemd
# and enables the timer to run at midnight every day.
#
# Usage:
#   sudo ./setup_auto_backup.sh          # Install and enable timer
#   sudo ./setup_auto_backup.sh status   # Check timer status
#   sudo ./setup_auto_backup.sh disable  # Disable timer (can re-enable later)
#   sudo ./setup_auto_backup.sh remove   # Completely remove timer and service

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="pilotdeck-backup.service"
TIMER_FILE="pilotdeck-backup.timer"
SYSTEMD_DIR="/etc/systemd/system"
ENV_DIR="/etc/pilotdeck"
ENV_FILE="$ENV_DIR/backup.env"

if [[ ! -f "$ROOT_DIR/backup_db_snapshot.sh" ]]; then
  echo "[ERROR] backup_db_snapshot.sh not found in $ROOT_DIR"
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] This script must be run as root (use sudo)"
  exit 1
fi

CMD="${1:-install}"

case "$CMD" in
  install)
    echo "[INFO] Installing systemd timer for daily DB snapshot..."

    # Optional env file for cloud upload, custom paths, etc.
    mkdir -p "$ENV_DIR"
    if [[ ! -f "$ENV_FILE" ]]; then
      cat > "$ENV_FILE" <<EOF
# PilotDeck backup configuration (optional)
#
# Local paths:
# PM_DB_FILE=$ROOT_DIR/data/pm.db
# PM_BACKUP_FILE=$ROOT_DIR/data/pm_backup.db
#
# Optional cloud upload:
# PM_BACKUP_UPLOAD_URL=https://...        # pre-signed URL or upload endpoint
# PM_BACKUP_UPLOAD_TOKEN=...             # optional bearer token
# PM_BACKUP_UPLOAD_METHOD=PUT            # PUT (default) or POST
EOF
      chmod 600 "$ENV_FILE" || true
    fi

    # Write service + timer with the current repo path.
    cat > "$SYSTEMD_DIR/$SERVICE_FILE" <<EOF
[Unit]
Description=PilotDeck Daily SQLite Snapshot
After=network.target

[Service]
Type=oneshot
WorkingDirectory=$ROOT_DIR
EnvironmentFile=-$ENV_FILE
ExecStart=/bin/bash $ROOT_DIR/backup_db_snapshot.sh
SyslogIdentifier=pilotdeck-backup

[Install]
WantedBy=multi-user.target
EOF

    cat > "$SYSTEMD_DIR/$TIMER_FILE" <<EOF
[Unit]
Description=PilotDeck Daily Backup Timer (runs at midnight)
Requires=pilotdeck-backup.service

[Timer]
OnCalendar=*-*-* 00:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
    
    # Reload systemd to recognize new units
    systemctl daemon-reload
    
    # Enable and start the timer (not the service directly)
    systemctl enable "$TIMER_FILE"
    systemctl start "$TIMER_FILE"
    
    echo "[SUCCESS] Timer installed and started."
    echo ""
    echo "=== Timer Status ==="
    systemctl status "$TIMER_FILE" --no-pager || true
    echo ""
    echo "=== Next Scheduled Run ==="
    systemctl list-timers "$TIMER_FILE" --no-pager || true
    echo ""
    echo "[INFO] A SQLite snapshot will be generated at midnight (00:00) every day."
    echo "[INFO] Check logs: journalctl -u pilotdeck-backup.service -f"
    echo "[INFO] Optional cloud upload config: $ENV_FILE"
    ;;
    
  status)
    echo "=== Timer Status ==="
    systemctl status "$TIMER_FILE" --no-pager || true
    echo ""
    echo "=== Next Scheduled Run ==="
    systemctl list-timers "$TIMER_FILE" --no-pager || true
    echo ""
    echo "=== Recent Snapshot Logs (last 20 lines) ==="
    journalctl -u pilotdeck-backup.service -n 20 --no-pager || true
    ;;
    
  disable)
    echo "[INFO] Disabling timer (can be re-enabled later)..."
    systemctl stop "$TIMER_FILE" || true
    systemctl disable "$TIMER_FILE" || true
    systemctl daemon-reload
    echo "[SUCCESS] Timer disabled."
    ;;
    
  remove)
    echo "[INFO] Removing timer and service..."
    systemctl stop "$TIMER_FILE" || true
    systemctl disable "$TIMER_FILE" || true
    rm -f "$SYSTEMD_DIR/$SERVICE_FILE"
    rm -f "$SYSTEMD_DIR/$TIMER_FILE"
    systemctl daemon-reload
    systemctl reset-failed || true
    echo "[SUCCESS] Timer and service removed."
    ;;
    
  *)
    echo "Usage: sudo $0 [install|status|disable|remove]"
    echo ""
    echo "Commands:"
    echo "  install  - Install and enable daily backup timer (default)"
    echo "  status   - Check timer status and view recent logs"
    echo "  disable  - Disable timer (can re-enable with 'install')"
    echo "  remove   - Completely remove timer and service"
    exit 1
    ;;
esac
