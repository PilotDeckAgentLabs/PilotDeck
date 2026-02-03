# 数据库运维（SQLite）

PilotDeck 使用嵌入式 SQLite 作为运行时数据源。

## 文件

- 主库：`data/pm.db`
- WAL 侧文件（WAL 模式正常现象）：`data/pm.db-wal`、`data/pm.db-shm`
- 快照备份（单文件）：`data/pm_backup.db`
- 恢复回滚文件（恢复时生成）：`data/pm.db.bak.<timestamp>`

## 环境变量

- `PM_DB_FILE`：SQLite DB 路径（默认 `data/pm.db`）
- `PM_ADMIN_TOKEN`：管理员口令（访问 `/api/admin/*` 必需）

可选（快照上传）：

- `PM_BACKUP_UPLOAD_URL`：上传地址或预签名 URL
- `PM_BACKUP_UPLOAD_TOKEN`：Bearer token（可选）
- `PM_BACKUP_UPLOAD_METHOD`：HTTP 方法（默认 `PUT`）

## 启动（本地）

```bash
python -m pip install -r requirements.txt
export PM_DB_FILE=./data/pm.db
export PM_ADMIN_TOKEN="<your-strong-token>"
python server/main.py
```

## 备份

### UI 导出（推荐）

1) 打开 UI 的运维面板
2) 输入 `PM_ADMIN_TOKEN`
3) 点击“导出备份（下载）”

结果：浏览器下载 `pm_backup_YYYYMMDDTHHMMSSZ.db`。

### CLI 快照

跨平台：

```bash
python scripts/sqlite_backup.py --db data/pm.db --out data/pm_backup.db
```

Linux 便捷脚本：

```bash
./backup_db_snapshot.sh
```

### 可选：生成快照后自动上传

`backup_db_snapshot.sh` 在生成快照后可执行上传（opt-in），需要设置：

- `PM_BACKUP_UPLOAD_URL`
- `PM_BACKUP_UPLOAD_TOKEN`（可选）
- `PM_BACKUP_UPLOAD_METHOD`（可选）

推荐做法：使用对象存储的预签名 URL（PUT）。

## 恢复

### UI 恢复

1) 打开 UI 的运维面板
2) 输入 `PM_ADMIN_TOKEN`
3) 点击“从备份恢复”，选择 `pm_backup_*.db`

服务端行为：

- 旧库保存为 `pm.db.bak.<timestamp>`
- 原子替换 `pm.db`

### CLI 恢复（服务器侧）

恢复前先停服务：

```bash
sudo systemctl stop pilotdeck
./restore_db_snapshot.sh --from ./data/pm_backup.db --force
sudo systemctl start pilotdeck
```

## 定时备份（systemd，opt-in）

默认不开启自动备份。

安装并启用每日 timer：

```bash
sudo ./setup_auto_backup.sh
```

会安装：

- `pilotdeck-backup.service`
- `pilotdeck-backup.timer`

配置文件（不存在则自动创建）：`/etc/pilotdeck/backup.env`

查看状态与日志：

```bash
sudo ./setup_auto_backup.sh status
journalctl -u pilotdeck-backup.service -f
```

## 健康检查

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

## 故障排查

- `database is locked`：确认没有多个服务实例同时指向同一个 `PM_DB_FILE`；避免在恢复期间进行高频写入；仅在确有需要时再考虑调整 `busy_timeout`。
- 快照安全：WAL 模式下不建议直接把 `pm.db` 当作安全备份；优先使用 UI 导出或 `scripts/sqlite_backup.py`。
