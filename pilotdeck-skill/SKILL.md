---
name: pilotdeck-skill
description: Create and run a PilotDeck project-sync workflow for agents. Use when you need to keep a local project status file in sync with PilotDeck, update project fields, write events, or manage agent runs via the PilotDeck Agent API.
---

# PilotDeck Skill

## Overview

Maintain a local project status file and sync changes to PilotDeck using runs, actions, and events. Follow the workflow to keep updates auditable and conflict-safe.

## Workflow

1) Read the status file (`pilotdeck/status.yaml` or `pilotdeck/status/<project-id>.yaml`).
2) Validate required fields (`project.id`, `project.name`, `pilotdeck.base_url`, `status.*`).
3) If missing, generate the status file from `docs/product/PROJECT_STATUS_TEMPLATE.md` and populate known fields (project name, base URL, project ID).
4) Resolve project identity:
   - Try `GET /api/projects/<project.id>` first.
   - If 404 or missing, search by `project.name` via `GET /api/projects` (client-side filtering).
   - If not found, create via `POST /api/projects` with `name: project.name`.
   - Update status file with resolved/created `project.id`.
5) Create a run via `POST /api/agent/runs` (include `projectId`, `agentId`, `title`). Note: `agentId` should be provided by the agent runtime, not from status file.
6) Sync status fields:
   - Use `POST /api/agent/actions` for `status.lifecycle`, `status.priority`, `status.progress`, and `status.tags`.
   - Use `PATCH /api/projects/<id>` for other custom fields as needed.
7) Write an event via `POST /api/agent/events` with the rationale and `before/after` data.
8) Update the run via `PATCH /api/agent/runs/<id>` with `summary`, `status`, `finishedAt`.
9) Write back `sync_state` and `activity_log` to the status file.

## Conflict Handling

- Always send `ifUpdatedAt` with `PATCH /api/projects/<id>`.
- On HTTP 409: fetch the latest project, reconcile, update the status file, then retry.

## Event Conventions

- `type`: `status-change` | `milestone` | `risk` | `note`
- `level`: `info` | `warn` | `error`
- `data`: `{ "before": {...}, "after": {...} }`

## References

- `docs/product/PROJECT_STATUS_TEMPLATE.md`
- `docs/agent/PILOTDECK_SKILL.md`
- `docs/agent/AGENT_API.md`
