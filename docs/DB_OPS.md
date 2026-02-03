# Database Ops (SQLite)

PilotDeck uses an embedded SQLite database as the runtime source of truth.

## Files

- Primary DB: `data/pm.db`
- WAL sidecars (normal in WAL mode): `data/pm.db-wal`, `data/pm.db-shm`
- Snapshot backup (single file): `data/pm_backup.db`
- Restore rollback file (created by restore): `data/pm.db.bak.<timestamp>`

## Environment Variables

- `PM_DB_FILE`: SQLite DB path (default `data/pm.db`)
- `PM_ADMIN_TOKEN`: admin token (required for `/api/admin/*`)

Optional (snapshot upload):

- `PM_BACKUP_UPLOAD_URL`: upload endpoint or pre-signed URL
- `PM_BACKUP_UPLOAD_TOKEN`: bearer token (optional)
- `PM_BACKUP_UPLOAD_METHOD`: HTTP method (default `PUT`)

## Start (Local)

```bash
python -m pip install -r requirements.txt
export PM_DB_FILE=./data/pm.db
export PM_ADMIN_TOKEN="<your-strong-token>"
python server/main.py
```

## Backup

### UI Export (recommended)

1) Open the Ops panel in the UI
2) Enter `PM_ADMIN_TOKEN`
3) Click “Export backup (download)”

Result: the browser downloads `pm_backup_YYYYMMDDTHHMMSSZ.db`.

### CLI Snapshot

Cross-platform:

```bash
python scripts/sqlite_backup.py --db data/pm.db --out data/pm_backup.db
```

Linux convenience wrapper:

```bash
./backup_db_snapshot.sh
```

### Optional: Upload After Snapshot

`backup_db_snapshot.sh` can upload the generated snapshot if you set:

- `PM_BACKUP_UPLOAD_URL`
- `PM_BACKUP_UPLOAD_TOKEN` (optional)
- `PM_BACKUP_UPLOAD_METHOD` (optional)

The recommended approach is to use a pre-signed URL from your object storage.

## Restore

### UI Restore

1) Open the Ops panel in the UI
2) Enter `PM_ADMIN_TOKEN`
3) Click “Restore from backup” and select a `pm_backup_*.db`

The server will:

- Save the previous DB as `pm.db.bak.<timestamp>`
- Replace `pm.db` atomically

### CLI Restore (server-side)

Stop the service first, then restore:

```bash
sudo systemctl stop pilotdeck
./restore_db_snapshot.sh --from ./data/pm_backup.db --force
sudo systemctl start pilotdeck
```

## Scheduled Backups (systemd, opt-in)

Auto backup is not enabled by default.

Install and enable the daily timer:

```bash
sudo ./setup_auto_backup.sh
```

This installs:

- `pilotdeck-backup.service`
- `pilotdeck-backup.timer`

Configuration file (created if missing): `/etc/pilotdeck/backup.env`

Check status/logs:

```bash
sudo ./setup_auto_backup.sh status
journalctl -u pilotdeck-backup.service -f
```

## Health Checks

```bash
python - <<'PY'
import sqlite3

db = 'data/pm.db'
conn = sqlite3.connect(db, timeout=5.0)
try:
    print('integrity_check:', conn.execute('PRAGMA integrity_check;').fetchone()[0])
    print('user_version:', conn.execute('PRAGMA user_version;').fetchone()[0])
finally:
    conn.close()
PY
```

## Troubleshooting

- `database is locked`: verify you are not running multiple server processes pointing to the same `PM_DB_FILE`; avoid heavy write traffic during restore/backup; consider increasing `busy_timeout` only if needed.
- Snapshot copy safety: in WAL mode, do not treat `pm.db` alone as a safe backup; prefer UI export or `scripts/sqlite_backup.py`.
