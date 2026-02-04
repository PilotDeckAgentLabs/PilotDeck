# Project Status Template (PilotDeck View)

This template lets agents keep a local “PilotDeck view” status document and sync it to PilotDeck as the source of truth.

## Placement

Recommended directory under repo root:

```
pilotdeck/
  status/
    <project-key>.yaml
```

For single-project repos, use `pilotdeck/status.yaml`.

## Update Cadence

- Update before and after each agent run.
- At least once per day when status is in-progress.
- Immediately when milestones/risks/decisions change.

## Status File Template (YAML)

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
    url: "docs/ARCHITECTURE.md"
  - title: "AGENT_API"
    url: "docs/AGENT_API.md"

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

## Field Mapping

- `status.lifecycle` → `projects.status`
- `status.priority` → `projects.priority`
- `status.progress` → `projects.progress`
- `status.category` → `projects.category`
- `status.tags` → `projects.tags`
- Other fields: can be written as custom fields via `PATCH /api/projects/<id>` if you want them visible in PilotDeck.

## Sync Principles

- Status file is the agent’s local source of truth.
- PilotDeck is the shared, auditable view.
- On `409` conflict: fetch latest project, reconcile, update status file, then retry.
