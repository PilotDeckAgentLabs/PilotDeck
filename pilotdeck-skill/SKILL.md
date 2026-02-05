---
name: pilotdeck-skill
description: Create and run a PilotDeck project-sync workflow for agents. Use when you need to keep a local project status file in sync with PilotDeck, update project fields, write events, or manage agent runs via the PilotDeck Agent API.
---

# PilotDeck Skill

## Overview

Maintain a local project status file and sync changes to PilotDeck using runs, actions, and events. Follow the workflow to keep updates auditable and conflict-safe.

## Workflow

1) Read the status file (`pilotdeck/status.yaml` or `pilotdeck/status/<project-key>.yaml`).
2) Validate required fields (`pilotdeck.base_url`, `pilotdeck.project_id`, `pilotdeck.agent_id`, `status.*`).
3) If missing, generate the status file from `docs/PROJECT_STATUS_TEMPLATE.md` and populate known fields (project name, base URL, project ID).
4) Create a run via `POST /api/agent/runs` (include `projectId`, `agentId`, `title`).
5) Sync status fields:
   - Use `POST /api/agent/actions` for `status.lifecycle`, `status.priority`, `status.progress`, and `status.tags`.
   - Use `PATCH /api/projects/<id>` for other custom fields as needed.
6) Write an event via `POST /api/agent/events` with the rationale and `before/after` data.
7) Update the run via `PATCH /api/agent/runs/<id>` with `summary`, `status`, `finishedAt`.
8) Write back `sync_state` and `activity_log` to the status file.

## Conflict Handling

- Always send `ifUpdatedAt` with `PATCH /api/projects/<id>`.
- On HTTP 409: fetch the latest project, reconcile, update the status file, then retry.

## Event Conventions

- `type`: `status-change` | `milestone` | `risk` | `note`
- `level`: `info` | `warn` | `error`
- `data`: `{ "before": {...}, "after": {...} }`

## References

- `docs/PROJECT_STATUS_TEMPLATE.md`
- `docs/PILOTDECK_SKILL.md`
- `docs/AGENT_API.md`
