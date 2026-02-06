# PilotDeck

English README: [README.en.md](./README.en.md)

PilotDeck 是面向个人开发者与团队内部的轻量项目管理与 Agent 协作审查平台。

产品定位（本仓库）：**Agent 驱动的 ProjectOps 与审计追踪**

- **项目推进**：以 `projects/runs/events/actions` 管理任务状态、进展与里程碑。
- **过程可审查**：Timeline 记录“谁在何时做了什么、为什么做、产生了什么影响”。
- **成本可观测**：通过 `usage` 上报和 `stats/tokens` 聚合观察 token/cost 趋势。

## 仓库边界

当前仓库只包含：

- `PilotDeck Server`（Flask + SQLite）
- `PilotDeck Web`（Vue 3）

不包含但已支持对接：

- `PilotDeckDesktop`（Windows 客户端，承载 AgentOps 主交互）
- `opencode-pilotdeck`（OpenCode 插件）

## 核心能力

- 轻量自托管：单文件 SQLite，无需额外数据库服务
- 多项目管理：状态、优先级、进度、标签、成本与收益
- Timeline 审计：事件 append-only，支持 run 归档与动作追踪
- 并发安全：`updatedAt + ifUpdatedAt` 乐观并发控制
- Agent 语义动作：`POST /api/agent/actions`（可选更新项目 + 自动写 event + 幂等）
- Agent 协作与审查：runs/events/actions 支持执行归档、证据沉淀与语义化写回
- Token 统计：
  - `POST /api/agent/usage` 上报 token/cost
  - `GET /api/stats/tokens` 聚合查询（按项目/Agent/workspace/model）

## 关键对象模型

- `Project`：项目事实状态（status/priority/progress/...）
- `Run`：一次 Agent 工作单元容器（开始到结束）
- `Event`：append-only 时间线记录（发生了什么/为什么）
- `Action`：语义化更新入口（常见字段变更 + 自动审计）
- `Agent Profile`：Agent 档案元数据（主要由 Desktop 侧管理）
- `Agent Capability`：能力包元数据（主要由 Desktop 侧管理）
- `Token Usage`：会话/运行成本记录

## 架构概览

- 后端：`server/mypm`
- 数据库：`data/pm.db`（默认）
- 前端：`frontend`（构建后由 Flask 静态服务）

推荐阅读：

- Agent API：`docs/AGENT_API.md` / `docs/AGENT_API.zh-CN.md`
- 架构说明：`docs/ARCHITECTURE.md` / `docs/ARCHITECTURE.zh-CN.md`
- 数据库运维：`docs/DB_OPS.md` / `docs/DB_OPS.zh-CN.md`
- PilotDeck Skill：`docs/PILOTDECK_SKILL.md` / `docs/PILOTDECK_SKILL.zh-CN.md`

## 给 PilotDeckDesktop / opencode-pilotdeck 的对接接口

运行与时间线：

- `POST /api/agent/runs`
- `PATCH /api/agent/runs/<runId>`
- `POST /api/agent/events`
- `POST /api/agent/actions`

Desktop Agent 配置（由本服务提供存储/API）：

- `GET/POST /api/agent/profiles`
- `GET/PATCH/DELETE /api/agent/profiles/<profileId>`
- `GET/POST /api/agent/capabilities`
- `GET/PATCH/DELETE /api/agent/capabilities/<capabilityId>`

Token 统计：

- `POST /api/agent/usage`（支持批量 `records`）
- `GET /api/agent/usage`
- `GET /api/stats/tokens`

建议插件在 `session.idle` 或 run 结束时上报 usage，以减少碎片写入。

## 本地开发

### 环境要求

- Python 3.10+
- Node.js 22.x（见 `NODE_VERSION.md`）

### 安装依赖

```bash
python -m pip install -r requirements.txt
```

```bash
cd frontend
npm ci
```

### 启动服务

后端：

```bash
python server/main.py
```

前端构建（首次或更新前端后）：

```bash
cd frontend
npm run build
```

默认访问：

- Web UI: `http://localhost:8689/`
- API: `http://localhost:8689/api`

## 环境变量

- `PM_PORT`：服务端口（默认 `8689`）
- `PM_DEBUG`：调试开关（默认 `0`）
- `PM_DB_FILE`：SQLite 文件路径（默认 `data/pm.db`）
- `PM_ADMIN_TOKEN`：管理接口口令（备份/恢复/部署）
- `PM_AGENT_TOKEN`：Agent API 口令

设置示例（PowerShell）：

```powershell
$env:PM_ADMIN_TOKEN = "<your-admin-token>"
$env:PM_AGENT_TOKEN = "<your-agent-token>"
python server\main.py
```

## 备份与恢复

可在 Web「运维」界面使用：

- 导出备份（下载 SQLite 快照）
- 从备份恢复（上传快照覆盖当前 DB）

详见：`docs/DB_OPS.md` / `docs/DB_OPS.zh-CN.md`

## 部署（Linux）

```bash
sudo ./deploy_pull_restart.sh
```

可选自动备份：

```bash
sudo ./setup_auto_backup.sh
```

## 路线方向

- 增强 Timeline 审查体验（证据、影响、回写建议）
- 优化多项目、多 Agent 成本归因与趋势分析
