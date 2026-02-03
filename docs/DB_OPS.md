# 后端数据库运维手册（SQLite / 零基础可用）

本项目后端使用本地嵌入式 SQLite 作为运行时主存储（WAL 模式）。

你不需要安装独立数据库服务（MySQL/Postgres），只要管理好几个文件即可。

---

## 0. 你需要记住的 3 件事

1) **主数据库文件**：默认是 `data/pm.db`（可通过 `PM_DB_FILE` 改路径）

2) **WAL 模式下不要直接复制 `pm.db` 当备份**：推荐用一致性快照脚本生成 `pm_backup.db`

3) **恢复前先停服务**：恢复本质是“替换数据库文件”，不停服务容易造成数据错乱

---

## 1. 我想启动服务（第一次 / 日常）

### 目标
启动后端 API（包含旧 UI `/` 和新 UI `/app` 的静态托管）。

### 动作

1) 安装依赖

```bash
python -m pip install -r requirements.txt
```

2) 启动服务

```bash
python server/main.py
```

3) 常用环境变量

- `PM_PORT`：端口（默认 `8689`）
- `PM_DEBUG`：调试（默认 `0`）
- `PM_DB_FILE`：SQLite DB 文件路径（默认 `data/pm.db`）

示例：

```bash
export PM_PORT=8689
export PM_DEBUG=0
export PM_DB_FILE=./data/pm.db
python server/main.py
```

---

## 2. 我想做一次备份（手动 / 立刻）

### 目标
生成一个**单文件**、可拷贝/可上传的数据库快照。

### 推荐动作（跨平台）

```bash
python scripts/sqlite_backup.py --db data/pm.db --out data/pm_backup.db
```

### 推荐动作（Web UI / 最简单）

目标：直接在浏览器里点击下载备份文件。

动作：
1) 打开系统页面，进入“运维”
2) 填写管理口令（环境变量 `PM_ADMIN_TOKEN`）
3) 点击“导出备份（下载）”
4) 浏览器会下载 `pm_backup_YYYYMMDDTHHMMSSZ.db`

你可以把这个文件保存到任何地方（本地硬盘、网盘、对象存储、Git 等）。

### 推荐动作（Linux 服务器脚本封装）

```bash
./backup_db_snapshot.sh
```

它会生成/覆盖：`data/pm_backup.db`

如需生成“带时间戳的多份备份”，可以自行指定输出文件，例如：

```bash
PM_BACKUP_FILE="data/pm_backup_$(date -u +%Y%m%dT%H%M%SZ).db" ./backup_db_snapshot.sh
```

### 备份上传到对象存储（手动，暂未集成）

把 `data/pm_backup.db` 上传到你的对象存储即可。
你可以按你偏好的工具完成：rclone / awscli / ossutil / coscmd 等。

建议做法：
- 本地保留最近 N 份（例如 7 份）
- 对象存储保留更久（例如 30/90/365 天），按成本与合规要求调整

---

## 2.1 我想“迁移到新机器”（换服务器/重装系统）

### 目标
在新机器上恢复到旧机器的同一份数据。

### 动作

1) 在旧机器生成快照：`data/pm_backup.db`
2) 把 `pm_backup.db` 复制到新机器的同一项目目录（建议放到 `data/pm_backup.db`）
3) 在新机器停止服务（如果已启动）
4) 执行恢复：

```bash
./restore_db_snapshot.sh --from ./data/pm_backup.db --force
```

5) 启动服务

---

## 3. 我想设置“每天自动备份”（Linux/systemd，可选）

### 目标
每天 00:00 自动生成一次 `data/pm_backup.db` 快照。

### 动作

说明：自动备份默认不启用。你需要手动安装 systemd timer。

1) 用 root 安装 timer

```bash
sudo ./setup_auto_backup.sh
```

2) 查看状态

```bash
sudo ./setup_auto_backup.sh status
```

3) 查看日志

```bash
journalctl -u pilotdeck-backup.service -f
```

说明：当前 timer 只负责生成快照；上传对象存储的步骤你可以后续再加（或等项目集成）。

---

## 4. 我想恢复数据（从快照）

### 目标
把系统回滚到某个快照时刻的数据状态。

### 安全提醒（必读）
恢复等同于覆盖 `pm.db`。
**务必先停服务**，否则可能出现“恢复完成但服务又写回旧状态”的问题。

### 动作（推荐流程）

1) 停服务

- systemd：`sudo systemctl stop pilotdeck`
- nohup 模式：停掉对应 PID

2) 执行恢复

```bash
./restore_db_snapshot.sh --from ./data/pm_backup.db --force
```

它会：
- 先把当前 `pm.db` 备份为 `pm.db.bak.<timestamp>`
- 再用快照覆盖 `pm.db`

3) 启服务

`sudo systemctl start pilotdeck`

### （可选）自动上传到云端

本项目不会默认绑定任何云厂商。你可以通过环境变量配置上传 endpoint（例如 OSS 的预签名 URL，或你自建的上传服务）：

- `PM_BACKUP_UPLOAD_URL`
- `PM_BACKUP_UPLOAD_TOKEN`（可选）
- `PM_BACKUP_UPLOAD_METHOD`（默认 PUT）

推荐方式：在服务器创建 `/etc/pilotdeck/backup.env`，写入上述环境变量，然后重启 timer：

```bash
sudo mkdir -p /etc/pilotdeck
sudo nano /etc/pilotdeck/backup.env

sudo systemctl restart pilotdeck-backup.timer
```

### 动作（Web UI / 最简单）

目标：在浏览器里选择一个备份文件并恢复。

动作：
1) 打开系统页面，进入“运维”
2) 填写管理口令（环境变量 `PM_ADMIN_TOKEN`）
3) 点击“从备份恢复”
4) 选择你之前下载的 `pm_backup_*.db`
5) 等待提示“恢复完成”，然后刷新页面

注意：恢复会覆盖当前数据库，后端会把旧数据库另存为 `pm.db.bak.<timestamp>`。

---

## 5. 我想确认数据库是否健康（排查用）

### 目标
确认 DB 文件可读、结构正常、没有明显损坏。

### 动作（无需 sqlite3 命令）

```bash
python - <<'PY'
import sqlite3

db = 'data/pm.db'
conn = sqlite3.connect(db, timeout=5.0)
try:
    print('db:', db)
    print('integrity_check:', conn.execute('PRAGMA integrity_check;').fetchone()[0])
    print('user_version:', conn.execute('PRAGMA user_version;').fetchone()[0])
finally:
    conn.close()
PY
```

---

## 6. 常见问题（按现象排查）

### 6.1 “database is locked” / 请求很慢

可能原因：
- 有多个进程同时写 DB，锁竞争严重
- 备份/恢复/脚本在高频运行

处理建议：
- 确认你不是“多个服务实例”同时指向同一个 `PM_DB_FILE`
- 优先用 `scripts/sqlite_backup.py` 做备份（避免粗暴复制文件）
- 需要时再提升 `busy_timeout`（代码已默认 5s）

### 6.2 `data/` 目录里出现 `pm.db-wal` / `pm.db-shm`

这是 WAL 模式的正常文件。

注意：
- 不要把这两个文件当作“需要单独备份的增量”；最稳妥的是用快照脚本生成单文件 `pm_backup.db`

### 6.3 升级代码后 DB 结构怎么办？

本项目在启动时会自动执行迁移（基于 `PRAGMA user_version`）。

你只需要：
1) 升级代码
2) 启动服务

如果升级前后你担心风险：先做一次快照备份（见第 2 节）。

---
