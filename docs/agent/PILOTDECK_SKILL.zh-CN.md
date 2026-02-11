# PilotDeckSkill 设计说明

本技能用于让 Agent 在推进项目时：
1) 更新本地状态文档；
2) 通过 Agent API 同步到 PilotDeck；
3) 保持审计轨迹（events / runs）。

## 能力范围

- 读取/验证项目状态文件（YAML）
- 启动与结束 Agent run
- 将状态变更同步到 PilotDeck
- 为关键变更写入 event
- 处理并发冲突（updatedAt + ifUpdatedAt）

## 输入与配置

- `statusFile`: 状态文件路径（默认 `pilotdeck/status.yaml`）
- `project.id`: PilotDeck 项目 ID（必填，映射到 `projects.id`）
- `project.name`: 项目显示名称（必填，映射到 `projects.name`）
- `baseUrl`: PilotDeck API base URL（默认来自状态文件 `pilotdeck.base_url`）
- `agentId`: Agent 标识（由 agent 运行时提供）
- `agentToken`: 优先读取环境变量 `PM_AGENT_TOKEN`（或 `X-PM-Token`）

## 工作流（推荐）

1) **读状态文件**，解析并校验必填字段。
2) **解析项目身份**：
   - 优先尝试 `GET /api/projects/<project.id>`。
   - 若返回 404 或缺失，则通过 `GET /api/projects` 按 `project.name` 搜索（客户端过滤）。
   - 若未找到，则通过 `POST /api/projects` 创建，使用 `name: project.name`。
   - 将解析或创建的 `project.id` 更新回状态文件。
3) **创建 run**：`POST /api/agent/runs`（包含 `projectId`/`agentId`/`title`）。
4) **同步项目字段**：
   - 优先用 `POST /api/agent/actions` 更新 `status/priority/progress/tags`。
   - 其他字段（如 `summary.goal`）用 `PATCH /api/projects/<id>` 写入自定义字段。
5) **写入事件**：`POST /api/agent/events` 记录"为何改变"。
6) **更新 run**：`PATCH /api/agent/runs/<id>` 写入 `summary`、`status`、`finishedAt`。
7) **写回本地状态文件**：更新 `sync_state.*` 与 `activity_log`。

## 变更映射规则

- `project.id` → `projects.id`（唯一标识符）
- `project.name` → `projects.name`（显示名称）
- `status.lifecycle` → action `set_status`
- `status.priority` → action `set_priority`
- `status.progress` → action `set_progress`
- `status.tags` → actions `add_tag` / `remove_tag`
- 其他字段（`summary` / `milestones` / `risks`）可写入项目自定义字段（可选）

## 幂等与冲突处理

- action `id` 建议使用稳定的 hash（`projectId + field + value + ts`）。
- `PATCH /projects/<id>` 必须携带 `ifUpdatedAt`。
- 若返回 `409`：重新 `GET /projects/<id>`，对比差异，更新本地状态文件后重试。

## 事件规范（建议）

- `type`: `status-change` / `milestone` / `risk` / `note`
- `level`: `info` / `warn` / `error`
- `title`: 简短动词短语
- `message`: 变更原因与影响
- `data`: `{ "before": {...}, "after": {...} }`

## 最小实现接口清单

- `GET /api/projects/<id>`
- `PATCH /api/projects/<id>`
- `POST /api/agent/runs`
- `PATCH /api/agent/runs/<id>`
- `POST /api/agent/actions`
- `POST /api/agent/events`

## 失败策略

- 网络失败：重试 1-3 次，退避 250ms -> 1s。
- 400/404：记录 event，标记 run 失败。
- 409：执行冲突流程（拉取最新 + 合并 + 重试）。
