# Agent API (PilotDeck)

This document is written for automation/agent clients.

Base URL: `http://<host>:<port>/api`

Response envelope:

```json
{
  "success": true,
  "data": { }
}
```

On failure, `success=false` and `error` is present. Some endpoints also return `message`.

## Auth (Optional)

This project is local-first.

- If `PM_AGENT_TOKEN` is NOT set in the server environment: agent endpoints are open.
- If `PM_AGENT_TOKEN` IS set: send header `X-PM-Agent-Token: <token>`.

Admin/ops endpoints (dangerous) are separate and require `PM_ADMIN_TOKEN` via `X-PM-Token`.

## Conventions

- Always send `Content-Type: application/json` for requests with a body.
- Prefer `PATCH` for partial updates.
- For concurrency safety in multi-agent scenarios:
  - Read the project first, capture its `updatedAt`.
  - Include `ifUpdatedAt` in your `PATCH` body.
  - If you receive HTTP `409`, re-fetch and retry with a new plan.

## Service Metadata

### GET `/meta`

Returns server capabilities and enums.

Example:

```bash
curl -s http://localhost:8689/api/meta
```

## Projects

### GET `/projects`

Query params:
- `status` (optional)
- `priority` (optional)
- `category` (optional)

### GET `/projects/<projectId>`

### POST `/projects`

Create a project.

Minimum body:

```json
{ "name": "My Project" }
```

### PUT `/projects/<projectId>`

Full update semantics (but implementation accepts partial updates).

### PATCH `/projects/<projectId>`

Partial update semantics.

Optional optimistic concurrency:

```json
{
  "ifUpdatedAt": "2026-01-30T12:34:56.000000",
  "status": "in-progress",
  "progress": 20
}
```

### POST `/projects/reorder`

Persist manual ordering:

```json
{ "ids": ["proj-aaa", "proj-bbb"] }
```

### POST `/projects/batch`

Batch patch multiple projects in one request.

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

Response includes per-op status (200/404/409/400) without failing the whole request.

## Stats

### GET `/stats`

Returns aggregated counts and financial totals.

## Agent Timeline (Events)

Events are append-only and stored in SQLite (`data/pm.db`).

Why events exist (important):

- Events are a **per-project execution trace**: what an agent did *to a project* (status/progress changes, notes, tags), plus any high-level milestones you want to audit.
- They are not limited to “API calls made”, but should reflect the **semantic intent and outcome**.
- In multi-agent parallel work, events provide: post-mortem, blame-free debugging, and reproducible run summaries.

### POST `/agent/events`

Create an event.

Body fields:
- `id` (optional, recommended for idempotency)
- `type` (string, default `note`)
- `level` (`info` | `warn` | `error`, default `info`)
- `projectId` (optional)
- `runId` (optional)
- `agentId` (optional)
- `title` (optional)
- `message` (optional)
- `data` (optional, any JSON)

Example:

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

If the same `id` is re-submitted, the server returns the existing event.

### GET `/agent/events`

Query params:
- `projectId`, `runId`, `agentId`, `type` (optional filters)
- `since` (optional ISO timestamp)
- `limit` (default 200, max 2000)

Example:

```bash
curl -s 'http://localhost:8689/api/agent/events?projectId=proj-aaa&limit=50'
```

## Agent Runs (Sessions)

Runs are stored in SQLite (`data/pm.db`).

Use a run to group a series of edits/actions.

- A run is a **container** (a unit of work).
- Events are the **timeline inside** that run.

### POST `/agent/runs`

Create a run.

Body:
- `id` (optional; if provided and already exists, server returns the existing run)
- `status` (default `running`)
- `projectId`, `agentId` (optional)
- `title`, `summary` (optional)
- `links` (optional array)
- `metrics` (optional object)
- `tags` (optional array)
- `meta` (optional object)

Example:

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

Query params: `projectId`, `agentId`, `status`, `limit` (max 500), `offset`.

### GET `/agent/runs/<runId>`

### PATCH `/agent/runs/<runId>`

Update a run status and attach summary/links/metrics.

Example:

```json
{
  "status": "succeeded",
  "finishedAt": "2026-01-30T12:34:56.000000",
  "summary": "Added /api/projects/batch + agent events"
}
```

## Recommended Agent Workflow

1) Call `GET /meta` to learn capabilities.
2) Load target projects via `GET /projects` (filter if possible).
3) Start a run via `POST /agent/runs` (keep the `runId`).
4) Before each mutation:
   - Read the project, capture `updatedAt`.
   - Apply changes via `PATCH /projects/<id>` with `ifUpdatedAt`.
5) After each significant step:
   - Append an event via `POST /agent/events` with `projectId` + `runId`.
6) Finish the run via `PATCH /agent/runs/<runId>`.

## Semantic Actions (Preferred)

If you want the agent to operate safely without knowing the full project schema, use the Actions API.

### POST `/agent/actions`

This endpoint:

- Applies a high-level action (e.g. set status / bump progress)
- Automatically writes a trace event (`id` is reused for idempotency)

Body:

```json
{
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
      "params": {"note": "Implemented /api/agent/actions and updated docs"}
    }
  ]
}
```

Supported action types:

- `set_status` params: `{ "status": "planning|in-progress|paused|completed|cancelled" }`
- `set_priority` params: `{ "priority": "low|medium|high|urgent" }`
- `set_progress` params: `{ "progress": 0..100 }`
- `bump_progress` params: `{ "delta": -100..100 }` (clamped to 0..100)
- `append_note` params: `{ "note": "...", "alsoWriteToProjectNotes": false }`
- `add_tag` params: `{ "tag": "..." }`
- `remove_tag` params: `{ "tag": "..." }`

Idempotency:

- Re-sending the same `id` will return the existing event and current project.
