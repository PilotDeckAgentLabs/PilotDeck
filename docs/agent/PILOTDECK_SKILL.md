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
- `pilotdeck.name`: canonical project name in PilotDeck (optional, falls back to `project.name`)
- `baseUrl`: PilotDeck API base URL (default from `pilotdeck.base_url`)
- `projectId`: PilotDeck project ID (default from `pilotdeck.project_id`)
- `agentId`: agent identifier (default from `pilotdeck.agent_id`)
- `agentToken`: read from `PM_AGENT_TOKEN` env (or `X-PM-Token`)

## Recommended Flow

1) **Read status file**, parse and validate required fields.
2) **Create run**: `POST /api/agent/runs` (include `projectId`/`agentId`/`title`).
3) **Sync project fields**:
   - Resolve display name by `pilotdeck.name` -> `project.name` and write it to `projects.name`.
   - Keep `pilotdeck.project_id` stable across related local repos if they should sync to one shared PilotDeck project.
   - Use `POST /api/agent/actions` for `status/priority/progress/tags`.
   - Use `PATCH /api/projects/<id>` for other custom fields (optional).
4) **Write event**: `POST /api/agent/events` to capture rationale.
5) **Update run**: `PATCH /api/agent/runs/<id>` with `summary`, `status`, `finishedAt`.
6) **Write back local status file**: update `sync_state.*` and `activity_log`.

## Mapping Rules

- `pilotdeck.name` (optional) -> `projects.name` (fallback: `project.name`)
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
