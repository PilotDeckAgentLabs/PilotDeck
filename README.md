# MyProjectManager

一个基于 GitHub 仓库的“个人项目统一管理”Demo：
- 项目数据以 `JSON` 文件形式存储在独立的数据仓库（便于版本管理、审计、回滚，也方便未来开源）
- 提供 Python CLI 脚本做数据管理（可选）
- 提供 Flask 后端 API + 原生 Web 前端，实现项目的增删改查与统计展示

## 功能

- 项目列表展示：名称、状态、优先级、分类、进度、预算、标签
- 条件筛选：状态 / 优先级 / 分类
- CRUD：新增 / 编辑 / 删除项目
- 统计：按状态/优先级/分类聚合 + 财务汇总

## 目录结构

- `data/`：数据仓库的工作目录（独立 Git 仓库，已在代码仓库中忽略）
- `data/projects.json`：项目数据（你日常维护的核心）
- `data/schema.json`：数据结构 JSON Schema（用于约束字段含义/结构）
- `scripts/project_manager.py`：CLI 数据管理脚本（增删改查/统计）
- `server/api_server.py`：后端 API + 静态前端托管
- `web/index.html`：前端页面
- `web/css/style.css`：前端样式
- `web/js/app.js`：前端逻辑（调用 API）

## 环境要求

- Python 3.8+（必需，建议 3.10+）

说明：本项目依赖（`requirements.txt`）要求 Python 3.8+。Linux 服务器上推荐使用 `/usr/local/bin/python3` 指向 Python 3.8+，避免改动 `/usr/bin/python`（可能影响 yum / 系统脚本）。

## 快速开始（本地运行）

### 0) 准备数据仓库（一次性）

本项目将 `data/` 作为“数据仓库”的工作目录（独立 Git 仓库，已在代码仓库中忽略）。

在代码仓库根目录执行（示例）：

```bash
git clone <your-data-repo-url> data
```

### 1) 安装依赖

在仓库根目录执行：

```bash
python -m pip install -r requirements.txt
```

### 2) 启动服务

方式 A（直接运行）：

```bash
python server/api_server.py
```

可选环境变量：

```bash
export PM_PORT=8689   # 端口，默认 8689
export PM_DEBUG=1     # 调试模式：1 开启，默认关闭
```

方式 B（Windows 脚本）：

```bat
start_server.bat
```

或 PowerShell：

```powershell
start_server.ps1
```

## 部署到云服务器（Linux）

本项目默认监听 `8689`。服务器部署场景使用 `deploy_pull_restart.sh` 一键拉取、安装依赖并重启服务。

仓库内已提供以下运维脚本：

1) 从 GitHub 拉取更新并部署、重启：`deploy_pull_restart.sh`
2) 将数据仓库的本地修改推送到 GitHub：`push_data_to_github.sh`
3) 拉取数据仓库更新：`pull_data_repo.sh`
4) 设置每天自动备份数据：`setup_auto_backup.sh`（推荐）

脚本说明见脚本文件头部注释。

### 1) 服务器初始化（一次性）

确保服务器已安装 Python 3.8+（例如已安装 `python3.8`），并按以下方式提供 `python3`：

```bash
ln -sf /usr/local/bin/python3.8 /usr/local/bin/python3
ln -sf /usr/local/bin/pip3.8 /usr/local/bin/pip3
python3 -V
```

注意：不要把 `/usr/bin/python` 指向 3.8（可能影响 yum / 系统脚本）。

### 2) 部署/更新（推荐运维方式）

在服务器仓库根目录执行：

```bash
./deploy_pull_restart.sh
```

脚本行为：
- `git pull --rebase` 拉取最新代码
- 使用 `${ROOT}/.venv` 创建虚拟环境并安装 `requirements.txt`
- 若存在 systemd：
  - 自动写入/启用 `/etc/systemd/system/myprojectmanager.service` 并重启
  - **自动设置每天定时备份数据到 GitHub**（幂等，无需手动操作）
- 若无 systemd：使用 `nohup` 启动（日志写入 `server.log`，PID 写入 `.server.pid`）

### 3) 常用运维命令（systemd）

```bash
systemctl status myprojectmanager
systemctl restart myprojectmanager
journalctl -u myprojectmanager -f
```

### 4) 自动数据备份

**好消息**：从最新版本开始，`deploy_pull_restart.sh` 会**自动设置**每天定时备份！

当你运行 `./deploy_pull_restart.sh` 时，脚本会：
- 自动安装 systemd timer（每天 0 点执行 `push_data_to_github.sh`）
- 自动启用并启动定时器
- 显示下次备份的时间

**无需手动操作**，部署即自动开启数据保护。

**管理自动备份**（可选）：

```bash
# 查看定时器状态和下次运行时间
systemctl status myprojectmanager-backup.timer
systemctl list-timers myprojectmanager-backup.timer

# 查看备份日志
journalctl -u myprojectmanager-backup.service -f

# 手动触发一次备份（测试）
sudo systemctl start myprojectmanager-backup.service

# 临时禁用自动备份
sudo systemctl stop myprojectmanager-backup.timer
sudo systemctl disable myprojectmanager-backup.timer

# 重新启用（下次 deploy 也会自动启用）
sudo systemctl enable myprojectmanager-backup.timer
sudo systemctl start myprojectmanager-backup.timer
```

**高级管理**（使用管理脚本）：

**高级管理**（使用管理脚本）：

```bash
# 使用独立管理脚本（与 deploy 脚本效果相同）
sudo ./setup_auto_backup.sh status   # 查看状态
sudo ./setup_auto_backup.sh disable  # 禁用
sudo ./setup_auto_backup.sh remove   # 完全移除
```

**备份特性**：
- **触发时间**：每天 00:00（午夜）
- **Persistent**：系统关机错过的备份会在下次启动时自动执行
- **RandomizedDelay**：随机延迟最多 30 分钟，避免负载集中
- **自动恢复**：每次运行 `deploy_pull_restart.sh` 都会确保定时器正常运行

### 5) 访问

- Web 界面：`http://<server-ip>:8689/`
- API 基地址：`http://<server-ip>:8689/api`
- 健康检查：`http://<server-ip>:8689/api/health`

本地默认端口为 `8689`（除非设置了 `PM_PORT`）。

## API 说明（简要）

- `GET /api/projects`：获取项目列表（支持 `status` / `priority` / `category` 查询参数）
- `GET /api/projects/{id}`：获取单个项目
- `POST /api/projects`：创建项目
- `PUT /api/projects/{id}`：更新项目
- `DELETE /api/projects/{id}`：删除项目
- `GET /api/stats`：统计信息

## CLI 脚本（可选）

列出项目：

```bash
python scripts/project_manager.py list
```

查看统计：

```bash
python scripts/project_manager.py stats
```

添加项目：

```bash
python scripts/project_manager.py add --name "示例项目" --status planning --priority medium --category "内容创作"
```

更新项目：

```bash
python scripts/project_manager.py update proj-001 --progress 50 --status in-progress
```

## 数据维护建议

- 你可以直接编辑 `data/projects.json`（JSON），并在 `data/` 目录内通过 Git 提交记录每次变更
- 如果多人协作：建议以 PR 的方式合并数据变更，避免冲突
