# PilotDeck

中文说明: [README.md](./README.md)

PilotDeck is a lightweight project management and Agent-collaboration review platform for individual developers and internal teams.

Positioning (this repository): **Agent-driven ProjectOps with auditability**

- **Project tracking**: manage status, progress, and milestones via `projects/runs/events/actions`.
- **Reviewable execution**: timeline answers who did what, when, why, and with what impact.
- **Cost observability**: ingest and analyze token/cost through `usage` + `stats/tokens`.

## Repository Scope

This repository includes:

- `PilotDeck Server` (Flask + SQLite)
- `PilotDeck Web` (Vue 3)

This repository does not include, but supports integration with:

- `PilotDeckDesktop` (Windows client, primary AgentOps UX)
- `opencode-pilotdeck` (OpenCode plugin)

## Core Capabilities

- Fast self-hosting: single SQLite file, no external DB required
- Multi-project management: status, priority, progress, tags, cost, revenue
- Timeline audit trail: append-only events + run grouping
- Safe concurrency: optimistic control via `updatedAt + ifUpdatedAt`
- Semantic agent actions: `POST /api/agent/actions` (optional mutation + auto event + idempotency)
- Agent collaboration and review: runs/events/actions provide execution history, evidence, and semantic writebacks
- Token tracking:
  - `POST /api/agent/usage` for usage/cost ingest
  - `GET /api/stats/tokens` for grouped analytics

## Domain Model

- `Project`: source of truth for project state
- `Run`: one agent work session container
- `Event`: append-only timeline record
- `Action`: semantic mutation entry with built-in audit behavior
- `Agent Profile`: agent profile metadata (primarily managed in Desktop)
- `Agent Capability`: capability metadata (primarily managed in Desktop)
- `Token Usage`: session/run cost records

## Architecture Overview

- Backend: `server/mypm`
- Database: `data/pm.db` (default)
- Frontend: `frontend` (served by Flask after build)

Recommended docs:

- Agent API: `docs/AGENT_API.md` / `docs/AGENT_API.zh-CN.md`
- Architecture: `docs/ARCHITECTURE.md` / `docs/ARCHITECTURE.zh-CN.md`
- DB operations: `docs/DB_OPS.md` / `docs/DB_OPS.zh-CN.md`
- PilotDeck Skill: `docs/PILOTDECK_SKILL.md` / `docs/PILOTDECK_SKILL.zh-CN.md`

## Integration APIs for PilotDeckDesktop / opencode-pilotdeck

Run and timeline:

- `POST /api/agent/runs`
- `PATCH /api/agent/runs/<runId>`
- `POST /api/agent/events`
- `POST /api/agent/actions`

Desktop agent configuration (stored via this service APIs):

- `GET/POST /api/agent/profiles`
- `GET/PATCH/DELETE /api/agent/profiles/<profileId>`
- `GET/POST /api/agent/capabilities`
- `GET/PATCH/DELETE /api/agent/capabilities/<capabilityId>`

Token analytics:

- `POST /api/agent/usage` (supports batch `records`)
- `GET /api/agent/usage`
- `GET /api/stats/tokens`

Recommendation: report usage on `session.idle` or run completion to avoid noisy writes.

## Local Development

### Requirements

- Python 3.10+
- Node.js 22.x (see `NODE_VERSION.md`)

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

```bash
cd frontend
npm ci
```

### Run

Backend:

```bash
python server/main.py
```

Build frontend:

```bash
cd frontend
npm run build
```

Default endpoints:

- Web UI: `http://localhost:8689/`
- API: `http://localhost:8689/api`

## Environment Variables

- `PM_PORT` (default `8689`)
- `PM_DEBUG` (default `0`)
- `PM_DB_FILE` (default `data/pm.db`)
- `PM_ADMIN_TOKEN` (admin endpoints: backup/restore/deploy)
- `PM_AGENT_TOKEN` (agent endpoints)

PowerShell example:

```powershell
$env:PM_ADMIN_TOKEN = "<your-admin-token>"
$env:PM_AGENT_TOKEN = "<your-agent-token>"
python server\main.py
```

## Backup and Restore

Use the Web "Ops" page to:

- Export backup (download SQLite snapshot)
- Restore from backup (upload snapshot)

Details: `docs/DB_OPS.md` / `docs/DB_OPS.zh-CN.md`

## Linux Deployment

```bash
sudo ./deploy_pull_restart.sh
```

Optional daily backup:

```bash
sudo ./setup_auto_backup.sh
```

## Roadmap Direction

- Stronger timeline review UX (evidence, impact, writeback suggestions)
- Deeper multi-project, multi-agent cost attribution and trends
