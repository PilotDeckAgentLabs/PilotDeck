# 项目状态模板（PilotDeck 视角）

本模板用于让 Agent 在本地项目中维护“PilotDeck 视角”的状态文档，并作为同步到 PilotDeck 的数据源。

## 放置位置

推荐在项目根目录创建目录：`pilotdeck/`，并在其中为每个项目创建一份状态文件：

```
pilotdeck/
  status/
    <project-key>.yaml
```

单项目仓库可简化为：`pilotdeck/status.yaml`。

## 更新节奏

- 每次 Agent 开始推进前与结束后各更新一次。
- 至少每日更新一次（若项目处于 in-progress）。
- 发生关键决策、里程碑或风险变化时立即更新。

## 状态文件模板（YAML）

```yaml
schema_version: 1

project:
  key: "my-project"
  name: "My Project"
  repo: "https://example.com/org/my-project"
  owner: "team-or-person"

pilotdeck:
  base_url: "http://localhost:8689/api"
  project_id: "proj-aaa"
  agent_id: "opencode/sisyphus"
  agent_token_env: "PM_AGENT_TOKEN"

status:
  lifecycle: "in-progress" # planning|in-progress|paused|completed|cancelled
  priority: "high" # low|medium|high|urgent
  progress: 35 # 0..100
  category: "backend"
  tags: ["agent", "pilotdeck", "api"]

summary:
  goal: "Provide agent-driven project tracking"
  success_criteria:
    - "PilotDeck sync works with optimistic concurrency"
    - "Status doc updated per run"

milestones:
  - name: "Agent API integration"
    status: "done" # todo|doing|done|blocked
    due: "2026-02-15"
    notes: "Run/event/action flows implemented"
  - name: "Status template + skill"
    status: "doing"
    due: "2026-02-20"

next_actions:
  - "Define status template schema"
  - "Implement PilotDeckSkill sync"

risks:
  - title: "Concurrent updates"
    impact: "Progress overwrite"
    mitigation: "Use updatedAt + ifUpdatedAt"

dependencies:
  - name: "PilotDeck server"
    status: "available"
    notes: "Local instance required for sync"

links:
  - title: "ARCHITECTURE"
    url: "docs/ARCHITECTURE.zh-CN.md"
  - title: "AGENT_API"
    url: "docs/AGENT_API.zh-CN.md"

activity_log:
  - ts: "2026-02-04T15:30:00+08:00"
    author: "opencode/sisyphus"
    summary: "Drafted status template"
    details: "Added schema v1 with pilotdeck sync fields"

sync_state:
  last_sync_at: "2026-02-04T15:35:00+08:00"
  last_sync_result: "success"
  last_project_updated_at: "2026-02-04T15:35:00.000000"
```

## 字段说明与映射

- `status.lifecycle` → `projects.status`
- `status.priority` → `projects.priority`
- `status.progress` → `projects.progress`
- `status.category` → `projects.category`
- `status.tags` → `projects.tags`
- 其他字段：作为自定义字段可通过 `PATCH /api/projects/<id>` 写入（若你希望在 PilotDeck 内也可见）

## 同步原则

- 状态文件是 Agent 的“本地真实源”。
- PilotDeck 是“协作视角的可审计视图”。
- 遇到 `409`（updatedAt 冲突）时：先拉取最新项目并对比，再更新本地状态文件并重试。
