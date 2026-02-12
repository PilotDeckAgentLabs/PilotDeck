# PilotDeck Skill 与 status.yaml 优化建议（通用版）

本文档基于实际使用体验总结，面向 PilotDeck 能力本身，不依赖任何具体项目。

---

## 1. 关键问题回顾（抽象）

1. **凭据校验与真实服务行为不一致**
- Skill 默认把 `project_id / agent_id / api_token` 视为必填。
- 但有些部署模式下，即使为空也可完成远端同步（例如通过开放 API + projectId）。

2. **状态文件字段语义不稳定**
- `project.key`、`project.id`、`pilotdeck.project_id` 可能同时存在，优先级不明确。
- `sync_state` 位置与缩进容易出错，导致状态不可解析。

3. **API 约定缺少“能力探测”**
- 不同实例支持的 action type 不一致（例如 `status.lifecycle` 可能不被支持）。
- Skill 未先探测接口能力，直接提交导致失败重试成本高。

4. **日志与同步状态闭环不完整**
- 常见“本地已更新，远端失败”状态缺少标准枚举。
- run/event/action 的关联 ID 未强制回写状态文件，审计链不完整。

---

## 2. 对 pilotdeck-skill 的优化建议

## 2.1 增加“同步模式”

建议在 Skill 内支持三种模式：

- `local_only`：仅更新本地状态与日志
- `remote_preferred`：优先远端，失败自动回退本地
- `remote_required`：远端失败则整体失败

并支持自动判定：

- 若 health/runs 接口可用且 project 可解析，自动尝试 `remote_preferred`

## 2.2 增加“API 能力探测阶段”

在真正同步前执行：

1. `GET /health`
2. `GET /projects` + project 解析
3. `POST /agent/runs` 试探
4. action/event 类型白名单探测（或读取服务端元数据）

输出 `capability_report`，再决定提交策略。

## 2.3 action 提交策略优化

当前建议：

- 若 action type 不支持，自动降级到 `PATCH /projects/{id}` 字段更新
- action 失败不应阻断 run/event 提交

即：`actions` 是增强能力，不应成为“唯一更新通道”。

## 2.4 project 解析策略标准化

建议优先级：

1. `pilotdeck.project_id`
2. `project.id`
3. 按 `project.name` 在 `/projects` 中模糊匹配（唯一命中）

匹配结果必须回写 `resolved_project_id` 到 `sync_state`。

## 2.5 run/event 审计闭环

每次同步后强制回写：

- `sync_state.last_run_id`
- `sync_state.last_event_id`（可选）
- `sync_state.last_sync_at`
- `sync_state.remote_result`（success/partial/failed）

---

## 3. 对 status.yaml 的优化建议

## 3.1 建议的最小稳定结构

```yaml
schema_version: 1

project:
  name: "..."
  id: "..."          # 本地项目标识

pilotdeck:
  base_url: "..."
  project_id: ""      # 可空，允许动态解析
  agent_id: ""        # 可空
  api_token: ""       # 可空（部分服务模式）
  sync_mode: "remote_preferred"  # local_only / remote_preferred / remote_required

status:
  lifecycle: "development"
  priority: "high"
  progress: 60
  tags: []

sync_state:
  sync_status: "not_started"
  last_sync_at: null
  last_run_id: null
  last_event_id: null
  resolved_project_id: null
  remote_result: null
  errors: []

activity_log: []
```

## 3.2 sync_status 枚举建议

统一为以下枚举，避免自由文本：

- `not_started`
- `local_updated`
- `remote_synced`
- `remote_synced_partial`
- `remote_sync_failed`
- `remote_unavailable`

## 3.3 进度字段规范

- `status.progress` 强约束为 `0..100` 整数
- 每次变化必须写 `activity_log` 的 before/after

## 3.4 时间字段规范

- 统一 ISO 8601 UTC（例如 `2026-02-12T03:39:20Z`）
- 禁止混用本地时区字符串

---

## 4. 失败处理与重试策略建议

1. **幂等键**
- run/event/action 建议带 `idempotency_key`，避免重复提交。

2. **冲突处理**
- `PATCH /projects/{id}` 必带 `ifUpdatedAt`。
- 409 时自动：拉最新 -> 合并 -> 重试一次。

3. **分级失败**
- run 创建失败：降级本地 only。
- action 失败：降级 PATCH。
- event 失败：记录 `sync_state.errors`，不回滚已成功更新。

---

## 5. 可观测性建议

建议 Skill 每次执行输出结构化结果：

- `mode_selected`
- `capability_report`
- `resolved_project_id`
- `remote_calls`（每步 status/code）
- `final_status`

这样可以快速定位“配置问题 vs 服务端能力问题”。

---

## 6. 落地优先级建议

P0（立即）：
- 增加 `sync_mode`
- 增加 project 解析优先级
- 统一 `sync_state` 枚举与字段

P1（短期）：
- 增加 capability 探测
- action 失败自动降级 PATCH

P2（中期）：
- 幂等键 + 冲突自动修复
- 执行结果结构化输出
