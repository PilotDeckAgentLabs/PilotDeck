#!/usr/bin/env bash
set -euo pipefail

# Setup automatic daily data backup using systemd timer
# This script installs myprojectmanager-backup.{service,timer} to systemd
# and enables the timer to run at midnight every day.
#
# Usage:
#   sudo ./setup_auto_backup.sh          # Install and enable timer
#   sudo ./setup_auto_backup.sh status   # Check timer status
#   sudo ./setup_auto_backup.sh disable  # Disable timer (can re-enable later)
#   sudo ./setup_auto_backup.sh remove   # Completely remove timer and service

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="myprojectmanager-backup.service"
TIMER_FILE="myprojectmanager-backup.timer"
SYSTEMD_DIR="/etc/systemd/system"

if [[ ! -f "$ROOT_DIR/$SERVICE_FILE" ]]; then
  echo "[ERROR] $SERVICE_FILE not found in $ROOT_DIR"
  exit 1
fi

if [[ ! -f "$ROOT_DIR/$TIMER_FILE" ]]; then
  echo "[ERROR] $TIMER_FILE not found in $ROOT_DIR"
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] This script must be run as root (use sudo)"
  exit 1
fi

CMD="${1:-install}"

case "$CMD" in
  install)
    echo "[INFO] Installing systemd timer for daily data backup..."
    
    # Copy service and timer files to systemd directory
    cp -f "$ROOT_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_FILE"
    cp -f "$ROOT_DIR/$TIMER_FILE" "$SYSTEMD_DIR/$TIMER_FILE"
    
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
    echo "[INFO] Data will be automatically pushed to GitHub at midnight (00:00) every day."
    echo "[INFO] Check logs: journalctl -u myprojectmanager-backup.service -f"
    ;;
    
  status)
    echo "=== Timer Status ==="
    systemctl status "$TIMER_FILE" --no-pager || true
    echo ""
    echo "=== Next Scheduled Run ==="
    systemctl list-timers "$TIMER_FILE" --no-pager || true
    echo ""
    echo "=== Recent Backup Logs (last 20 lines) ==="
    journalctl -u myprojectmanager-backup.service -n 20 --no-pager || true
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
