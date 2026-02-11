# Agent API（PilotDeck）

本文档面向自动化/Agent 客户端。

Base URL：`http://<host>:<port>/api`

## 响应包裹（Envelope）

成功：

```json
{
  "success": true,
  "data": {}
}
```

失败：

```json
{
  "success": false,
  "error": "...",
  "data": {}
}
```

说明：
- 失败时 `data` 可能为空，也可能携带结构化错误信息。
- 部分接口还会返回 `message`。

## 鉴权（可选）

PilotDeck 是 local-first。

- 如果环境变量未设置 `PM_AGENT_TOKEN`：Agent 接口默认开放
- 如果设置了 `PM_AGENT_TOKEN`：请求头必须带 `X-PM-Agent-Token: <token>`（或 `X-PM-Token`）

管理/运维接口单独隔离，需要 `PM_ADMIN_TOKEN`，请求头：`X-PM-Token`。

## HTTP 方法语义（速查）

- `GET`：读取
- `POST`：创建/追加/执行动作
- `PATCH`：部分更新（只更新你提交的字段）
- `PUT`：理论上是全量更新；本项目实现也可接受部分字段。建议优先使用 `PATCH`
- `DELETE`：删除

## 并发写入（updatedAt + ifUpdatedAt）

多 Agent 并发写入建议使用乐观并发控制：

1) `GET /projects/<projectId>` 读取项目，拿到 `updatedAt`
2) `PATCH` 时带上 `ifUpdatedAt`
3) 若返回 HTTP `409`，重新拉取项目并基于最新状态重新决策后重试

重要说明：
- `ifUpdatedAt` 是与当前 `updatedAt` 的“字符串完全一致”匹配
- 成功写入后服务端一定会刷新 `updatedAt`

## 核心概念（Run / Event / Action）

本 API 刻意把三件事拆开：

- 项目状态（`/projects/...`）
- 审计时间线（`/agent/events`）
- 工作会话聚合（`/agent/runs`）

定义：

- `run`：一次 Agent 工作会话/工作单元的容器。用于把一组 events/actions 归档到同一个 `runId`，并在结束时记录最终状态与总结。
- `event`：append-only 的时间线记录。回答“发生了什么、何时发生、谁做的、关联哪个项目/哪个 run、细节是什么”。
- `action`：语义化动作请求。在本项目里 actions 不会作为独立实体存表；每条 action 会写入一条 event（作为幂等键），并且可能更新项目。

关系：

- 一个 `run` 可以包含多条 `event`。
- 一条 `action` 一定产生一条 `event`（`event.id == action.id`）。
- 项目变更有两种写入方式：
  - `PATCH /projects/<projectId>`：只更新项目状态，不会自动写 event
  - `POST /agent/actions`：更新项目 + 自动写 event

如何选择：

- 需要更新任意字段（灵活）时：用 `PATCH /projects/<projectId>`，并显式写 `POST /agent/events`
- 只需要有限的常用动作，且希望内置幂等 + 自动审计时：用 `POST /agent/actions`

## 项目模型（常用字段）

项目以 JSON payload 形式存储，另有少量索引列用于筛选/排序。

常用字段：
- `id`（string，只读）
- `name`（string）
- `status`（string）：`planning|in-progress|paused|completed|cancelled`
- `priority`（string）：`low|medium|high|urgent`
- `category`（string|null）
- `progress`（int，0..100）
- `description`（string）
- `notes`（string）
- `tags`（string[]）
- `cost`（object，至少包含 `{ "total": number }`）
- `revenue`（object，至少包含 `{ "total": number }`）
- `createdAt`（string，只读）
- `updatedAt`（string，服务端维护）

自定义字段：
- 你可以通过 `PATCH`/`PUT` 写入额外的 JSON 字段。服务端会持久化，但不保证可被索引/筛选。

## 服务元信息

### GET `/meta`

返回服务能力集与枚举。

```bash
curl -s http://localhost:8689/api/meta
```

## 项目（Projects）

### GET `/projects`

Query 参数（可选）：
- `status`
- `priority`
- `category`

```bash
curl -s 'http://localhost:8689/api/projects?status=in-progress&priority=high'
```

### GET `/projects/<projectId>`

```bash
curl -s http://localhost:8689/api/projects/proj-aaa
```

### POST `/projects`

创建项目。

最小 body：

```json
{ "name": "My Project" }
```

### PATCH `/projects/<projectId>`

含义：
- 部分更新：只对你提交的字段生效
- 保护字段会被忽略：`id`、`createdAt`（以及 `ifUpdatedAt` 本身）
- 成功写入后服务端一定会刷新 `updatedAt`

请求 body：
- 任意项目字段子集
- 可选 `ifUpdatedAt`（乐观并发）

示例：更新状态与进度

```bash
curl -s -X PATCH http://localhost:8689/api/projects/proj-aaa \
  -H 'Content-Type: application/json' \
  -d '{
    "ifUpdatedAt": "2026-01-30T12:34:56.000000",
    "status": "in-progress",
    "progress": 20
  }'
```

示例：添加标签（tags 以完整数组形式存储）

```bash
curl -s -X PATCH http://localhost:8689/api/projects/proj-aaa \
  -H 'Content-Type: application/json' \
  -d '{
    "ifUpdatedAt": "2026-01-30T12:34:56.000000",
    "tags": ["api", "agent", "pilotdeck"]
  }'
```

成功响应：HTTP 200

```json
{
  "success": true,
  "data": { "id": "proj-aaa", "updatedAt": "...", "status": "in-progress" },
  "message": "项目更新成功"
}
```

冲突响应：HTTP 409

```json
{
  "success": false,
  "error": "Conflict: updatedAt mismatch",
  "data": { "message": "updatedAt mismatch: expected=... actual=..." }
}
```

### PUT `/projects/<projectId>`

更新项目（建议优先使用 `PATCH`）。

### DELETE `/projects/<projectId>`

删除项目。

### POST `/projects/reorder`

持久化手动排序：

```json
{ "ids": ["proj-aaa", "proj-bbb"] }
```

### POST `/projects/batch`

批量 patch。

```json
{
  "ops": [
    {
      "opId": "op-1",
      "id": "proj-aaa",
      "ifUpdatedAt": "...",
      "patch": { "status": "paused" }
    },
    {
      "opId": "op-2",
      "id": "proj-bbb",
      "patch": { "progress": 65 }
    }
  ]
}
```

响应会给出每条 op 的独立状态（200/404/409/400），避免“全有或全无”。

## 统计（Stats）

### GET `/stats`

返回按状态/优先级/分类的聚合统计与财务汇总。

### GET `/stats/tokens`

返回 token/cost 聚合统计（用于 Web 仪表盘）。

Query 参数（均可选）：
- `projectId`
- `agentId`
- `workspace`
- `source`
- `since`（ISO 时间，含边界）
- `until`（ISO 时间，含边界）

返回 `data` 包含：
- `totals`
- `byDay`
- `byProject`
- `byAgent`
- `byWorkspace`
- `byModel`

## AgentOps：Profiles 与 Capabilities

这些接口用于给 PilotDeckDesktop 管理可复用的 Agent 行为配置。

### Agent Profiles

- `GET /agent/profiles?enabled=true|false`
- `POST /agent/profiles`
- `GET /agent/profiles/<profileId>`
- `PATCH /agent/profiles/<profileId>`
- `DELETE /agent/profiles/<profileId>`

建议字段示例：

```json
{
  "id": "agent-desktop-planner",
  "name": "Desktop Planner",
  "role": "planner",
  "description": "先规划后执行的 Agent",
  "styleTags": ["cautious", "explainable"],
  "skills": ["pilotdeck-skill"],
  "outputMode": "concise",
  "writebackPolicy": "minimal",
  "permissions": {"filesystem": "write", "shell": "restricted"},
  "enabled": true,
  "meta": {"owner": "team-a"}
}
```

### Agent Capabilities

- `GET /agent/capabilities?enabled=true|false`
- `POST /agent/capabilities`
- `GET /agent/capabilities/<capabilityId>`
- `PATCH /agent/capabilities/<capabilityId>`
- `DELETE /agent/capabilities/<capabilityId>`

建议字段示例：

```json
{
  "id": "cap-default-delivery",
  "name": "Default Delivery",
  "description": "平衡速度与审计可追踪性",
  "promptPack": "Follow PilotDeck protocol and provide evidence.",
  "skillPack": ["pilotdeck-skill"],
  "constraints": ["No destructive git commands"],
  "enabled": true,
  "meta": {"version": "1.0.0"}
}
```

## Token 使用上报（供 `opencode-pilotdeck`）

用于插件或客户端上报 token/cost。

### POST `/agent/usage`

支持单条或批量（`records` 数组）。

单条示例：

```json
{
  "id": "usage-ses-abc123-001",
  "ts": "2026-02-06T10:00:00+08:00",
  "projectId": "proj-aaa",
  "runId": "run-1234",
  "agentId": "opencode/sisyphus",
  "workspace": "E:/work/PilotDeck",
  "sessionId": "ses-abc123",
  "source": "opencode-plugin",
  "model": "openai/gpt-5.3-codex",
  "promptTokens": 1200,
  "completionTokens": 560,
  "totalTokens": 1760,
  "cost": 0.42,
  "data": {
    "provider": "openai",
    "trigger": "session.idle"
  }
}
```

批量示例：

```json
{
  "records": [
    {
      "id": "usage-001",
      "projectId": "proj-aaa",
      "agentId": "opencode/sisyphus",
      "totalTokens": 100,
      "promptTokens": 70,
      "completionTokens": 30,
      "cost": 0.02
    },
    {
      "id": "usage-002",
      "projectId": "proj-aaa",
      "agentId": "opencode/sisyphus",
      "totalTokens": 80,
      "promptTokens": 55,
      "completionTokens": 25,
      "cost": 0.016
    }
  ]
}
```

幂等建议：
- `id` 对同一 usage 记录保持稳定（例如 `usage-<sessionId>-<seq>`）。
- 重复上报相同 `id` 不会重复入库。

### GET `/agent/usage`

Query 参数（可选）：
- `projectId`
- `agentId`
- `workspace`
- `source`
- `since`
- `until`
- `limit`（默认 200，最大 5000）

## 推荐上报流程（`opencode-pilotdeck`）

1) **解析项目身份**（从状态文件）：
   - 优先级 1：使用 `project.id` → `GET /api/projects/<id>`
   - 优先级 2：若返回 404 或缺失，则按 `project.name` 搜索 → `GET /api/projects`（客户端过滤）
   - 优先级 3：若未找到，则创建 → `POST /api/projects`，使用 `name: project.name`
   - 将解析或创建的 `project.id` 更新回状态文件
2) 任务/会话开始：`POST /agent/runs`
3) 关键节点：`POST /agent/events`
4) 项目变更：优先 `POST /agent/actions`（或 `PATCH /projects/<id>` + event）
5) 会话空闲或结束：`POST /agent/usage`
6) 收尾：`PATCH /agent/runs/<runId>`（写 `status`、`summary`、`finishedAt`）

## Agent 时间线（Events）

events 是 append-only，存储于 SQLite（`data/pm.db`）。

events 用于：
- 审计（发生了什么）
- 排障（为什么发生）
- 交接（关键决策与链接）

Event 结构（读取时可预期）：

```json
{
  "id": "evt-...",
  "ts": "2026-02-03T12:34:56.000000",
  "type": "note|action.set_status|...",
  "level": "debug|info|warn|error",
  "projectId": "proj-...",
  "runId": "run-...",
  "agentId": "...",
  "title": "...",
  "message": "...",
  "data": {}
}
```

### POST `/agent/events`

含义：
- 追加一条时间线记录。
- 如果你提供 `id`，该接口变为幂等。

适用场景：
- 你使用了 `PATCH /projects/...` 更新项目，需要补一条审计记录。
- 你要记录里程碑/决策/错误。

请求 body：
- `id`（可选；用于幂等）
- `type`（可选；默认 `note`）
- `level`（可选；默认 `info`）
- `projectId` / `runId` / `agentId`（可选关联）
- `title` / `message`（可选展示字段）
- `data`（可选；任意 JSON-ish 值）

响应：
- HTTP 201：创建成功
- HTTP 200 + `message: "event exists"`：同 `id` 的 event 已存在

```bash
curl -s -X POST http://localhost:8689/api/agent/events \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "evt-unique-001",
    "type": "status-change",
    "projectId": "proj-aaa",
    "agentId": "opencode/sisyphus",
    "message": "Set status to in-progress",
    "data": {"from": "planning", "to": "in-progress"}
  }'
```

幂等：
- 服务端按 `id` 去重。
- 重复发送相同 `id` 会返回已存在的 event，而不是插入新记录。

### GET `/agent/events`

含义：
- 查询 events（尽力按条件过滤）。

Query 参数（可选）：
- `projectId`：仅返回关联某项目的 events
- `runId`：仅返回关联某 run 的 events
- `agentId`：仅返回某 agent 的 events
- `type`：按 `event.type` 精确匹配
- `since`：ISO timestamp（含边界）
- `limit`：默认 200，最大 2000

排序：
- 返回按时间升序排列。

```bash
curl -s 'http://localhost:8689/api/agent/events?projectId=proj-aaa&limit=50'
```

## Agent Runs（会话/执行单元）

runs 存储于 SQLite（`data/pm.db`）。用于把一组 events/actions 组织成一个“工作单元”。

你可以把 run 理解为：
- 一次 Agent 工作会话（开始 -> 执行 -> 结束）
- 最终用来写总结/结果的顶层对象

Run 结构（读取时可预期）：

```json
{
  "id": "run-...",
  "projectId": "proj-...",
  "agentId": "...",
  "status": "running|success|failed|cancelled",
  "title": "...",
  "summary": "...",
  "createdAt": "...",
  "updatedAt": "...",
  "startedAt": "...",
  "finishedAt": "...",
  "links": [],
  "tags": [],
  "metrics": {},
  "meta": {}
}
```

### POST `/agent/runs`

含义：
- 创建 run（如果 `id` 已存在，则返回已有 run）。

适用场景：
- 你希望把一批 actions/events 归到一个工作单元里。
- 你希望有一个最终状态 + summary 用于审计与交接。

字段：
- `id`（可选）
- `status`（可选；默认 `running`）
- `projectId`, `agentId`（可选）
- `title`, `summary`（可选）
- `links`（可选数组）
- `metrics`（可选对象）
- `tags`（可选数组）
- `meta`（可选对象）

响应：
- HTTP 201：创建成功
- HTTP 200 + `message: "run exists"`：同 `id` 的 run 已存在

```bash
curl -s -X POST http://localhost:8689/api/agent/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "projectId": "proj-aaa",
    "agentId": "opencode/sisyphus",
    "title": "Implement agent API",
    "tags": ["api", "agent"]
  }'
```

### GET `/agent/runs`

含义：
- 列表查询 runs（支持过滤与分页）。

Query 参数（可选）：
- `projectId`
- `agentId`
- `status`
- `limit`（默认 50，最大 500）
- `offset`（默认 0）

### GET `/agent/runs/<runId>`

### PATCH `/agent/runs/<runId>`

含义：
- 对 run 元数据做部分更新。

保护字段：
- `id`、`createdAt` 会被忽略。

常见更新字段：
- `status`：`running|success|failed|cancelled`
- `finishedAt`：ISO timestamp（结束时设置）
- `summary`：简短总结
- `links` / `metrics` / `tags` / `meta`

```json
{
  "status": "success",
  "finishedAt": "2026-01-30T12:34:56.000000",
  "summary": "Added /api/projects/batch + agent events"
}
```

## 语义化 Actions（推荐）

当你希望以“高层动作”安全更新项目，并自动产出审计 event 时，使用该接口。

### POST `/agent/actions`

行为：
- 执行每条 action
- 可选更新项目（`recordOnly=true` 时不更新项目）
- 始终追加一条 event，且 `id == action.id`（作为幂等键）

副作用（单条 action）：
- 若 `recordOnly=false` 且该 action 生成了非空 patch，则会按 `PATCH /projects/<projectId>` 语义更新项目（包含 `updatedAt` 刷新 + normalize）。
- 无论是否更新项目，都会追加一条 event：
  - `type: "action.<actionType>"`
  - 请求里带了 `runId` 则写入 event.runId
  - `data.before` / `data.after`（status/priority/progress/tags）
  - `data.projectUpdatedAt`（项目更新后的 updatedAt；若 `recordOnly=true` 则是当前值）

请求 body：
- `agentId`（可选）
- `runId`（可选）
- `projectId`（可选：作为 action item 的默认 projectId）
- `actions`（必填：非空数组）

action item 字段：
- `id`（可选；建议提供以实现幂等）
- `projectId`（string；若未提供 top-level `projectId` 则必填）
- `type`（必填）
- `params`（object；可选）
- `recordOnly`（bool；可选；为 true 时不更新项目）
- `ifUpdatedAt`（string；可选；用于项目更新的乐观并发）

支持的 `type`：
- `set_status` params: `{ "status": "planning|in-progress|paused|completed|cancelled" }`
- `set_priority` params: `{ "priority": "low|medium|high|urgent" }`
- `set_progress` params: `{ "progress": 0..100 }`
- `bump_progress` params: `{ "delta": -100..100 }`（最终 clamp 到 0..100）
- `append_note` params: `{ "note": "...", "alsoWriteToProjectNotes": false }`
- `add_tag` params: `{ "tag": "..." }`
- `remove_tag` params: `{ "tag": "..." }`

示例：

```bash
curl -s -X POST http://localhost:8689/api/agent/actions \
  -H 'Content-Type: application/json' \
  -d '{
    "agentId": "opencode/sisyphus",
    "runId": "run-1234",
    "actions": [
      {
        "id": "act-unique-001",
        "projectId": "proj-aaa",
        "type": "set_status",
        "params": {"status": "in-progress"},
        "ifUpdatedAt": "2026-01-30T12:34:56.000000"
      },
      {
        "id": "act-unique-002",
        "projectId": "proj-aaa",
        "type": "bump_progress",
        "params": {"delta": 10}
      },
      {
        "id": "act-unique-003",
        "projectId": "proj-aaa",
        "type": "append_note",
        "params": {"note": "Implemented /api/agent/actions", "alsoWriteToProjectNotes": true}
      }
    ]
  }'
```

响应形态：HTTP 200

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "act-unique-001",
        "success": true,
        "status": 200,
        "projectId": "proj-aaa",
        "changed": true,
        "project": {},
        "event": {}
      }
    ],
    "changed": true,
    "lastUpdated": "..."
  }
}
```

单条 action 的失败会体现在 `results` 内（整体响应仍为 HTTP 200）：
- `status: 404`：项目不存在
- `status: 409`：`ifUpdatedAt` 冲突
- `status: 400`：action 输入不合法

幂等：
- 重复发送相同 `id` 会返回已存在的 event 与当前项目状态（并带 `message: "action exists"`）。

客户端提示：
- 需要更新任意项目字段（超出支持的 action types）时：用 `PATCH /projects/<projectId>` 并显式写 event。
- 不想手动处理 tags 数组的“读-改-写”时：优先用 actions 的 `add_tag/remove_tag`。

## 端到端 Agent 工作流示例

```bash
# 1) 获取能力与枚举
curl -s http://localhost:8689/api/meta

# 2) 选择项目
proj='proj-aaa'
cur=$(curl -s http://localhost:8689/api/projects/$proj)

# 3) 创建 run
run=$(curl -s -X POST http://localhost:8689/api/agent/runs -H 'Content-Type: application/json' -d '{"projectId":"proj-aaa","agentId":"my-agent","title":"Work"}')

# 4) 基于乐观并发更新项目（用你实际拉取到的 updatedAt 替换 <updatedAt>）
curl -s -X PATCH http://localhost:8689/api/projects/$proj \
  -H 'Content-Type: application/json' \
  -d '{"ifUpdatedAt":"<updatedAt>","progress":30,"status":"in-progress"}'

# 5) 写入审计 event
curl -s -X POST http://localhost:8689/api/agent/events \
  -H 'Content-Type: application/json' \
  -d '{"type":"note","projectId":"proj-aaa","message":"Updated progress to 30%"}'
```
