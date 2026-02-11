# PilotDeckSkill Design

This skill lets an agent:
1) update the local status document,
2) sync changes to PilotDeck via Agent API,
3) preserve an auditable trail (events / runs).

## Scope

- Read/validate status YAML
- Start and finish agent runs
- Sync status changes to PilotDeck
- Write events for key changes
- Handle optimistic concurrency (updatedAt + ifUpdatedAt)

## Inputs and Config

- `statusFile`: status file path (default `pilotdeck/status.yaml`)
- `project.id`: PilotDeck project ID (required, maps to `projects.id`)
- `project.name`: project display name (required, maps to `projects.name`)
- `baseUrl`: PilotDeck API base URL (default from `pilotdeck.base_url`)
- `agentId`: agent identifier (provided by agent runtime)
- `agentToken`: read from `PM_AGENT_TOKEN` env (or `X-PM-Token`)

## Recommended Flow

1) **Read status file**, parse and validate required fields.
2) **Resolve project identity**:
   - Try `GET /api/projects/<project.id>` first.
   - If 404 or missing, search by `project.name` via `GET /api/projects` (client-side filtering).
   - If not found, create via `POST /api/projects` with `name: project.name`.
   - Update status file with resolved/created `project.id`.
3) **Create run**: `POST /api/agent/runs` (include `projectId`/`agentId`/`title`).
4) **Sync project fields**:
   - Use `POST /api/agent/actions` for `status/priority/progress/tags`.
   - Use `PATCH /api/projects/<id>` for other custom fields (optional).
5) **Write event**: `POST /api/agent/events` to capture rationale.
6) **Update run**: `PATCH /api/agent/runs/<id>` with `summary`, `status`, `finishedAt`.
7) **Write back local status file**: update `sync_state.*` and `activity_log`.

## Mapping Rules

- `project.id` → `projects.id` (unique identifier)
- `project.name` → `projects.name` (display name)
- `status.lifecycle` → action `set_status`
- `status.priority` → action `set_priority`
- `status.progress` → action `set_progress`
- `status.tags` → actions `add_tag` / `remove_tag`
- Other fields (`summary` / `milestones` / `risks`) can be stored as custom project fields (optional)

## Idempotency and Conflicts

- Use stable action `id` (hash of `projectId + field + value + ts`).
- `PATCH /projects/<id>` must include `ifUpdatedAt`.
- On `409`: `GET /projects/<id>`, reconcile, update status file, retry.

## Event Convention

- `type`: `status-change` / `milestone` / `risk` / `note`
- `level`: `info` / `warn` / `error`
- `title`: short verb phrase
- `message`: rationale and impact
- `data`: `{ "before": {...}, "after": {...} }`

## Minimal API Surface

- `GET /api/projects/<id>`
- `PATCH /api/projects/<id>`
- `POST /api/agent/runs`
- `PATCH /api/agent/runs/<id>`
- `POST /api/agent/actions`
- `POST /api/agent/events`

## Failure Policy

- Network errors: retry 1-3 times with backoff 250ms -> 1s.
- 400/404: write an event, mark run failed.
- 409: conflict flow (fetch latest + merge + retry).
