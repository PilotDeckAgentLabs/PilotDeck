# Agent API (PilotDeck)

This document targets automation / agent clients.

Base URL: `http://<host>:<port>/api`

## Response Envelope

Success:

```json
{
  "success": true,
  "data": {}
}
```

Failure:

```json
{
  "success": false,
  "error": "...",
  "data": {}
}
```

Notes:
- `data` on failures is optional and may contain structured details.
- Some endpoints also return `message`.

## Auth (Optional)

PilotDeck is local-first.

- If `PM_AGENT_TOKEN` is NOT set: agent endpoints are open.
- If `PM_AGENT_TOKEN` IS set: send `X-PM-Agent-Token: <token>` (or `X-PM-Token`).

Admin/ops endpoints are separate and require `PM_ADMIN_TOKEN` via `X-PM-Token`.

## HTTP Method Semantics (Quick Primer)

- `GET`: read.
- `POST`: create, append, or perform an action.
- `PATCH`: partial update (only the fields you send are updated).
- `PUT`: full update in HTTP theory; in this codebase it behaves like an update and accepts partial payloads. Prefer `PATCH`.
- `DELETE`: delete.

## Concurrency (updatedAt + ifUpdatedAt)

To safely write in multi-agent environments:

1) `GET /projects/<projectId>` and capture `updatedAt`.
2) Send your `PATCH` including `ifUpdatedAt`.
3) On HTTP `409`, re-fetch and retry with a new plan.

Important:
- `ifUpdatedAt` is an exact string match against the current `updatedAt`.
- On success, the server always sets a fresh `updatedAt`.

## Core Concepts (Run / Event / Action)

This API intentionally separates:

- Project state (stored in `/projects/...`)
- Audit trail (stored in `/agent/events`)
- Work-session grouping (stored in `/agent/runs`)

Definitions:

- `run`: a container for one agent work session. Use it to group many events/actions under a single `runId`, record final outcome, and attach summary/metrics.
- `event`: append-only timeline record. It answers: what happened, when, by whom, on which project/run, and with what details.
- `action`: a semantic operation request. In this codebase, actions are not stored as a separate entity; each action writes an event (idempotency key) and may mutate the project.

Relationship:

- One `run` can have many `events`.
- One `action` always produces exactly one `event` (with `event.id == action.id`).
- A project mutation can be done by:
  - `PATCH /projects/<projectId>` (pure state update; no automatic event)
  - `POST /agent/actions` (state update + automatic event)

Choose the endpoint:

- Use `PATCH /projects/<projectId>` when you need full flexibility (any field), and you will also write events explicitly.
- Use `POST /agent/actions` when you want:
  - a small, safe action vocabulary
  - built-in idempotency
  - automatic timeline event

## Project Model (Common Fields)

The server stores projects as JSON payloads, with a few indexed columns.

Common fields:
- `id` (string, read-only)
- `name` (string)
- `status` (string): `planning|in-progress|paused|completed|cancelled`
- `priority` (string): `low|medium|high|urgent`
- `category` (string|null)
- `progress` (int 0..100)
- `description` (string)
- `notes` (string)
- `tags` (string[])
- `cost` (object, at least `{ "total": number }`)
- `revenue` (object, at least `{ "total": number }`)
- `createdAt` (string, read-only)
- `updatedAt` (string, server-managed)

Custom fields:
- You may write additional JSON fields via `PATCH`/`PUT`. They will be persisted, but not necessarily indexed.

## Service Metadata

### GET `/meta`

Returns server capabilities and enums.

```bash
curl -s http://localhost:8689/api/meta
```

## Projects

### GET `/projects`

Query params (optional):
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

Create a project.

Request body (minimum):

```json
{ "name": "My Project" }
```

### PATCH `/projects/<projectId>`

Meaning:
- Partial update: only fields present in the JSON body are applied.
- Protected fields are ignored: `id`, `createdAt` (and `ifUpdatedAt`).
- The server always updates `updatedAt`.

Request body:
- Any subset of project fields
- Optional `ifUpdatedAt` for optimistic concurrency

Example: update status and progress

```bash
curl -s -X PATCH http://localhost:8689/api/projects/proj-aaa \
  -H 'Content-Type: application/json' \
  -d '{
    "ifUpdatedAt": "2026-01-30T12:34:56.000000",
    "status": "in-progress",
    "progress": 20
  }'
```

Example: add a tag (tags are stored as a full array)

```bash
curl -s -X PATCH http://localhost:8689/api/projects/proj-aaa \
  -H 'Content-Type: application/json' \
  -d '{
    "ifUpdatedAt": "2026-01-30T12:34:56.000000",
    "tags": ["api", "agent", "pilotdeck"]
  }'
```

Success response: HTTP 200

```json
{
  "success": true,
  "data": { "id": "proj-aaa", "updatedAt": "...", "status": "in-progress" },
  "message": "项目更新成功"
}
```

Conflict response: HTTP 409

```json
{
  "success": false,
  "error": "Conflict: updatedAt mismatch",
  "data": { "message": "updatedAt mismatch: expected=... actual=..." }
}
```

### PUT `/projects/<projectId>`

Update a project. Prefer `PATCH`.

### DELETE `/projects/<projectId>`

Delete a project.

### POST `/projects/reorder`

Persist manual ordering.

```json
{ "ids": ["proj-aaa", "proj-bbb"] }
```

### POST `/projects/batch`

Batch patch multiple projects.

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

Use events for:
- auditability (what happened)
- debugging (why did state change)
- handoff (summaries and links)

Event shape (what you can expect on reads):

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

Meaning:
- Append a timeline record.
- If you provide `id`, the endpoint becomes idempotent.

When to use:
- You used `PATCH /projects/...` and want an audit record.
- You want to log a milestone / decision / error.

Request body:
- `id` (optional; if present, used for idempotency)
- `type` (optional; default `note`)
- `level` (optional; default `info`)
- `projectId` / `runId` / `agentId` (optional linkage)
- `title` / `message` (optional display fields)
- `data` (optional; any JSON-ish value)

Responses:
- HTTP 201: created
- HTTP 200 + `message: "event exists"`: the same `id` already exists

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

Idempotency:
- The server checks existence by `id`.
- Re-sending the same `id` returns the existing event instead of inserting a new one.

### GET `/agent/events`

Meaning:
- List events (best-effort filter).

Query params (optional):
- `projectId`: only events attached to a project
- `runId`: only events attached to a run
- `agentId`: only events from an agent
- `type`: exact match on `event.type`
- `since`: ISO timestamp (inclusive)
- `limit`: default 200, max 2000

Ordering:
- Returned in ascending time order.

```bash
curl -s 'http://localhost:8689/api/agent/events?projectId=proj-aaa&limit=50'
```

## Agent Runs

Runs are stored in SQLite (`data/pm.db`). A run groups a series of events/actions.

Think of a run as:
- one agent "work session" (start -> steps -> finish)
- the top-level record you summarize at the end

Run shape (what you can expect on reads):

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

Meaning:
- Create a new run (or return existing if `id` already exists).

When to use:
- You want to group a batch of actions/events into a single unit of work.
- You want a final status + summary for audit/handoff.

Body fields:
- `id` (optional)
- `status` (optional; default `running`)
- `projectId`, `agentId` (optional)
- `title`, `summary` (optional)
- `links` (optional array)
- `metrics` (optional object)
- `tags` (optional array)
- `meta` (optional object)

Responses:
- HTTP 201: created
- HTTP 200 + `message: "run exists"`: the same `id` already exists

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

Meaning:
- List runs with filtering and pagination.

Query params (optional):
- `projectId`
- `agentId`
- `status`
- `limit` (default 50, max 500)
- `offset` (default 0)

### GET `/agent/runs/<runId>`

### PATCH `/agent/runs/<runId>`

Meaning:
- Partial update for run metadata.

Protected fields:
- `id`, `createdAt` are ignored.

Common fields to patch:
- `status`: `running|success|failed|cancelled`
- `finishedAt`: ISO timestamp (set when finishing)
- `summary`: short human-readable summary
- `links` / `metrics` / `tags` / `meta`

```json
{
  "status": "success",
  "finishedAt": "2026-01-30T12:34:56.000000",
  "summary": "Added /api/projects/batch + agent events"
}
```

## Semantic Actions (Preferred)

Use this endpoint when you want safe, schema-light project mutations with an automatic audit event.

### POST `/agent/actions`

Behavior:
- Executes each action
- Optionally patches the project (unless `recordOnly=true`)
- Always appends an event with `id == action.id` (idempotency key)

Side effects (per action):
- If `recordOnly=false` and the action implies a non-empty patch, the project is updated via `PATCH /projects/<projectId>` semantics (including `updatedAt` refresh + normalization).
- An event is always appended with:
  - `type: "action.<actionType>"`
  - `runId` (if provided on request)
  - `data.before` / `data.after` (status/priority/progress/tags)
  - `data.projectUpdatedAt` (the project's `updatedAt` after mutation, or current if `recordOnly=true`)

Request body:
- `agentId` (optional)
- `runId` (optional)
- `projectId` (optional default for action items)
- `actions` (required non-empty array)

Action item fields:
- `id` (optional; recommended for idempotency)
- `projectId` (string; required unless top-level `projectId` is provided)
- `type` (required)
- `params` (object; optional)
- `recordOnly` (bool; optional; when true, no project mutation)
- `ifUpdatedAt` (string; optional; optimistic concurrency for project mutation)

Supported `type`:
- `set_status` params: `{ "status": "planning|in-progress|paused|completed|cancelled" }`
- `set_priority` params: `{ "priority": "low|medium|high|urgent" }`
- `set_progress` params: `{ "progress": 0..100 }`
- `bump_progress` params: `{ "delta": -100..100 }` (clamped to 0..100)
- `append_note` params: `{ "note": "...", "alsoWriteToProjectNotes": false }`
- `add_tag` params: `{ "tag": "..." }`
- `remove_tag` params: `{ "tag": "..." }`

Example:

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

Response shape: HTTP 200

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

Per-action failure is reported inside `results` (the overall response is still HTTP 200):
- `status: 404` when project not found
- `status: 409` when `ifUpdatedAt` conflicts
- `status: 400` for invalid action input

Idempotency:
- Re-sending the same `id` returns the existing event and current project (with `message: "action exists"`).

Notes for clients:
- If you need to update arbitrary project fields (beyond the supported action types), use `PATCH /projects/<projectId>` and write your own event.
- If you want "add/remove tag" semantics without fetching/merging arrays, prefer actions.

## End-to-End Agent Workflow Example

```bash
# 1) Discover capabilities
curl -s http://localhost:8689/api/meta

# 2) Pick a project
proj='proj-aaa'
cur=$(curl -s http://localhost:8689/api/projects/$proj)

# 3) Start a run
run=$(curl -s -X POST http://localhost:8689/api/agent/runs -H 'Content-Type: application/json' -d '{"projectId":"proj-aaa","agentId":"my-agent","title":"Work"}')

# 4) Patch project with optimistic concurrency (replace <updatedAt> with the real value you fetched)
curl -s -X PATCH http://localhost:8689/api/projects/$proj \
  -H 'Content-Type: application/json' \
  -d '{"ifUpdatedAt":"<updatedAt>","progress":30,"status":"in-progress"}'

# 5) Append an audit event
curl -s -X POST http://localhost:8689/api/agent/events \
  -H 'Content-Type: application/json' \
  -d '{"type":"note","projectId":"proj-aaa","message":"Updated progress to 30%"}'
```
