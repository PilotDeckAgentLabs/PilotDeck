# PilotDeck

面向开发者个人与团队内部的轻量项目管理与 Agent 协作控制台。

- 快速部署、自托管：Flask + SQLite 单文件数据库，无需独立 DB 服务
- Agent 深度介入：Agent 可通过 API 记录 runs/events/actions，并以可审计的方式更新项目进度与里程碑
- 适合并行推进：同时管理多个项目与多个 Agent，减少“口头同步”和“进度漂移”

## 适用场景

- 个人/独立开发：跟踪多个项目的状态、优先级、成本与收益
- 团队内部使用：在内网/私有环境共享项目台账与执行记录，用于协作与交接
- Agent 驱动开发流程：让 Agent 自动推进项目并写回进度、里程碑与变更原因
- 多 Agent 并行：通过 `updatedAt + ifUpdatedAt` 的乐观并发控制，降低并发写入冲突

## 核心能力

- 项目管理：状态、优先级、分类、进度、标签、成本/收益
- Agent API：
  - runs：一次工作流/会话的容器
  - events：项目级执行轨迹（可审计、可回放、便于复盘）
  - actions：面向 Agent 的语义化操作入口（自动写 event、支持幂等）
- 备份/恢复（最简单可理解的方式）：
  - 导出备份：浏览器下载 SQLite 快照文件
  - 从备份恢复：上传快照文件覆盖当前数据库

## 架构概览

- 后端：`server/mypm`（Flask API）
- 数据库：SQLite（默认 `data/pm.db`）
- 前端：
  - 旧 UI（无需构建）：`/`
  - 新 UI（Vue 3，构建后可用）：`/app`

文档：
- Agent 客户端对接：`docs/AGENT_API.md`
- 数据库运维（备份/恢复/排障）：`docs/DB_OPS.md`

## 快速开始（本地）

### 1) 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2) 启动服务

```bash
python server/main.py
```

默认访问：
- UI：`http://localhost:8689/`
- API：`http://localhost:8689/api`

### 2.1) 构建新 UI（可选）

构建后可访问：`http://localhost:8689/app`

```bash
cd frontend
npm install
npm run build
```

### 3) 可选环境变量

- `PM_PORT`：端口（默认 8689）
- `PM_DEBUG`：调试（默认 0）
- `PM_DB_FILE`：SQLite DB 文件路径（默认 `data/pm.db`）
- `PM_ADMIN_TOKEN`：运维口令（备份/恢复/部署等敏感接口需提供请求头 `X-PM-Token`）
- `PM_AGENT_TOKEN`：Agent 口令（设置后 Agent API 需提供 `X-PM-Agent-Token`）

#### PM_ADMIN_TOKEN 如何设置

本项目不会提供默认口令。你需要在运行服务的环境里显式设置 `PM_ADMIN_TOKEN`。

本地（macOS/Linux，临时生效）：

```bash
export PM_ADMIN_TOKEN="<your-strong-token>"
python server/main.py
```

本地（Windows PowerShell，临时生效）：

```powershell
$env:PM_ADMIN_TOKEN = "<your-strong-token>"
python server\main.py
```

Linux 服务器（systemd，推荐持久化）：

1) 编辑你的服务 unit（例如 `/etc/systemd/system/pilotdeck.service`）在 `[Service]` 下增加：

```ini
Environment=PM_ADMIN_TOKEN=<your-strong-token>
```

2) 使配置生效：

```bash
sudo systemctl daemon-reload
sudo systemctl restart pilotdeck
```

设置后，在 UI 的“运维”中填写该口令即可使用导出备份/恢复等操作。

## 备份与恢复（推荐从 UI 开始）

1) 进入 UI 的“运维”
2) 填写 `PM_ADMIN_TOKEN`
3) 点击：
   - “导出备份（下载）”：下载 `pm_backup_*.db`
   - “从备份恢复”：选择并上传 `pm_backup_*.db`

更完整说明与排障：`docs/DB_OPS.md`

## 部署到 Linux 服务器（可选）

仓库提供 `deploy_pull_restart.sh` 一键拉取代码、安装依赖、构建前端并重启服务。

```bash
sudo ./deploy_pull_restart.sh
```

注：脚本会尝试安装 systemd service；也支持无 systemd 的 nohup 模式。

### （可选）启用每日自动备份

自动备份默认不启用。需要你在服务器上手动安装 systemd timer：

```bash
sudo ./setup_auto_backup.sh
```

如果你希望自动上传到云端（例如 OSS 预签名 URL / 自建上传服务），编辑：`/etc/pilotdeck/backup.env`。

## 命名说明

代码层面仍可能使用历史名称（例如 systemd service、包名等）。本 README 将产品对外名称统一为 PilotDeck。

## 贡献与扩展方向

- 更完善的 Agent Skill 管理与项目推进流程编排
- 更清晰的项目模型（里程碑/交付物/文档生成）
- 更细粒度的权限与审计
