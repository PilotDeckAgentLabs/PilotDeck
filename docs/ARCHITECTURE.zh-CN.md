# PilotDeck 工程架构

本文档用于项目 Owner（工程师）快速理解当前工程的模块划分与职责边界。以“功能是什么”为主，必要处简要说明实现方式。

## 概览

PilotDeck 是可自托管的轻量项目管理与 Agent 协作控制台。

- 运行时存储：SQLite（`data/pm.db`），WAL 模式
- 后端：Flask API（app factory + blueprints）
- UI：
  - Vue UI：`frontend/` 构建后产物 `frontend/dist/`，路径 `/`（需要构建）
- Agent 集成：runs/events/actions，用于 Agent 写回进度并形成可审计轨迹
- 运维：管理员备份导出/恢复；可选部署触发；可选 systemd 定时快照

## 目录结构

- `server/`
  - `server/main.py`：服务入口（读取环境变量并启动 Flask）
  - `server/mypm/`：后端包
 - `frontend/`：新 UI（Vue 3 + TS，构建输出到 `frontend/dist/`）
- `scripts/`：辅助脚本（例如 SQLite 快照备份）
- `docs/`：工程/运维/接口文档
- `data/`：运行时数据目录（git 忽略）

## 后端（Flask）

### 应用工厂

- `server/mypm/app.py`
  - 创建 Flask app、加载 `Config`、初始化 store/service、注册蓝图
  - 静态资源托管：`/` -> `frontend/dist/`（SPA fallback）
  - 恢复数据库期间的保护：使用内存标记 `restoring_db`，对非 `/api/admin/*` 请求返回 503（降低“恢复中写入”的风险）

### 配置

- `server/mypm/config.py`
  - 路径：`ROOT_DIR`、`DATA_DIR`、`DB_FILE`、`FRONTEND_DIST_DIR`
  - 认证：`PM_ADMIN_TOKEN`、`PM_AGENT_TOKEN`
  - 部署集成：deploy 状态/日志文件、systemd unit 前缀

### 领域（domain）

- `server/mypm/domain/models.py`
  - Project / AgentRun / AgentEvent 的字段归一化
  - 默认值填充、时间戳字段统一等
- `server/mypm/domain/enums.py`
  - 项目状态/优先级枚举（UI 与 `/api/meta` 使用）
- `server/mypm/domain/auth.py`
  - 请求头鉴权：
    - Admin：`X-PM-Token` 必须匹配 `PM_ADMIN_TOKEN`
    - Agent：若配置了 `PM_AGENT_TOKEN`，则 `X-PM-Agent-Token` 必须匹配
- `server/mypm/domain/errors.py`
  - 服务层/接口层共享异常类型

### 存储层（SQLite）

- `server/mypm/storage/sqlite_db.py`
  - 连接与 PRAGMA：WAL、busy_timeout、foreign_keys 等（每连接生效）
  - schema migrations：基于 `PRAGMA user_version`
  - 当前主要表：
    - `projects`
    - `agent_runs`
    - `agent_events`
    - `agent_profiles`（Agent 档案）
    - `agent_capabilities`（PromptPack + SkillPack 能力包）
    - `token_usage_records`（token/cost 用量上报）
    - `meta`（KV 元信息）
- `server/mypm/storage/sqlite_store.py`
  - `ProjectsStore`：项目列表/创建/更新/删除/排序/批量更新 + 统计
  - `AgentRunsStore`：runs 的 create/get/list/patch
  - `AgentEventsStore`：events 的 append/exists/list
  - 设计取舍：完整 payload 保存在 `payload_json`，同时维护少量可索引字段用于筛选/排序

### 服务层（services）

- `server/mypm/services/project_service.py`
  - 项目 CRUD 与并发控制
  - 使用 `updatedAt` / `ifUpdatedAt` 做乐观并发（多 Agent 并行写入时关键）
- `server/mypm/services/agent_service.py`
  - runs 业务逻辑（包含幂等创建）
- `server/mypm/services/deploy_service.py`
  - 通过执行 `deploy_pull_restart.sh` 启动部署任务
  - 通过状态文件与日志文件暴露部署状态

### API 蓝图（api）

- `server/mypm/api/meta.py`
  - `/api/health`：健康检查
  - `/api/meta`：能力集、枚举、鉴权要求（UI 与 Agent 客户端使用）
- `server/mypm/api/projects.py`
  - `/api/projects`：list/create
  - `/api/projects/<id>`：get/put/patch/delete
  - `/api/projects/reorder`：排序持久化
  - `/api/projects/batch`：批量 patch（单条失败不影响整体）
- `server/mypm/api/stats.py`
  - `/api/stats`：聚合统计与财务汇总
  - `/api/stats/tokens`：token/cost 聚合统计
- `server/mypm/api/agent.py`
  - `/api/agent/runs`、`/api/agent/runs/<id>`
  - `/api/agent/events`
  - `/api/agent/actions`：语义化动作入口（更新项目 + 写入 trace event）
- `server/mypm/api/agent_ops.py`
  - `/api/agent/profiles`：Agent 档案 CRUD
  - `/api/agent/capabilities`：能力包 CRUD
  - `/api/agent/usage`：token 用量上报/查询
- `server/mypm/api/admin_ops.py`
  - `/api/admin/backup`（GET）：导出一致性 SQLite 快照（下载）
  - `/api/admin/restore`（POST）：上传快照并原子替换数据库
  - `/api/admin/deploy`、`/deploy/status`、`/deploy/log`：可选的“后端触发部署”

## 前端

### 新 UI（Vue 3）

- `frontend/src/`
  - `frontend/src/api/client.ts`：Typed API client
  - `frontend/src/stores/*`：Pinia 状态
  - `frontend/src/components/*`：CRUD/运维组件
- 构建输出：`frontend/dist/`，后端在 `/` 下托管

## 运维与部署

- `deploy_pull_restart.sh`
  - Linux：拉取代码、安装依赖、构建前端、重启 systemd 服务
  - 不默认启用自动备份（opt-in）
- `backup_db_snapshot.sh`
  - 生成一致性 SQLite 快照（调用 Python online backup API）
  - 可选上传：`PM_BACKUP_UPLOAD_URL` / `PM_BACKUP_UPLOAD_TOKEN` / `PM_BACKUP_UPLOAD_METHOD`
- `restore_db_snapshot.sh`
  - CLI 恢复：用快照覆盖 `pm.db`（要求先停服务）
- `setup_auto_backup.sh`
  - 安装 `pilotdeck-backup.service` / `pilotdeck-backup.timer`
  - 生成 `/etc/pilotdeck/backup.env`（可选上传配置）

## 关键流程

### Agent 写回进度（推荐模式）

1) 读取项目 `GET /api/projects/<id>`，拿到 `updatedAt`
2) 更新项目 `PATCH /api/projects/<id>` 并携带 `ifUpdatedAt`（或使用 `/api/agent/actions`）
3) 写入事件 `POST /api/agent/events`，必要时更新 run 状态 `PATCH /api/agent/runs/<id>`

### 备份导出与恢复

- 导出：`GET /api/admin/backup` -> 返回可下载的 SQLite 快照
- 恢复：`POST /api/admin/restore` -> 上传快照并原子替换 `data/pm.db`
