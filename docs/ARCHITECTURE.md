# PilotDeck Architecture

This document describes the current architecture at a module level. It is written for project owners (engineers).

## Overview

PilotDeck is a self-hosted project hub for developer workflows with optional agent integration.

- Runtime storage: SQLite (`data/pm.db`) in WAL mode
- Backend: Flask API (app factory + blueprints)
- UI:
  - Vue UI built from `frontend/` and served at `/` (requires build)
- Agent integration: runs/events/actions endpoints for agent-driven progress updates and audit trail
- Ops: backup export/restore via admin endpoints; optional deploy trigger and systemd scripts

## Repository Layout

- `server/`
  - `server/main.py`: main entrypoint (reads env, starts Flask)
  - `server/mypm/`: backend package
- `frontend/`: Vue 3 UI (build outputs to `frontend/dist/`)
- `scripts/`: helper CLIs (e.g. SQLite snapshot)
- `docs/`: owner and client documentation
- `data/`: runtime data directory (ignored by git)

## Backend (Flask)

### Application Factory

- `server/mypm/app.py`
  - Creates Flask app, loads `Config`, initializes stores/services, registers blueprints
  - Serves `/` from `frontend/dist` when built (SPA fallback)
  - Maintains a small in-memory maintenance flag (`restoring_db`) to block API calls during restore

### Configuration

- `server/mypm/config.py`
  - Paths: `ROOT_DIR`, `DATA_DIR`, `DB_FILE`, `FRONTEND_DIST_DIR`
  - Auth tokens: `PM_ADMIN_TOKEN`, `PM_AGENT_TOKEN`
  - Deploy integration: state/log files and systemd unit prefix

### Domain

- `server/mypm/domain/models.py`
  - Normalization for Project, AgentRun, AgentEvent payloads
  - Defaults and field normalization (e.g., timestamps, required fields)
- `server/mypm/domain/enums.py`
  - Project status/priority enums used by UI/meta endpoints
- `server/mypm/domain/auth.py`
  - Header-based auth gates:
    - Admin: `X-PM-Token` must match `PM_ADMIN_TOKEN`
    - Agent: `X-PM-Agent-Token` must match `PM_AGENT_TOKEN` (if configured)
- `server/mypm/domain/errors.py`
  - Shared exception types for services/API error mapping

### Storage Layer (SQLite)

- `server/mypm/storage/sqlite_db.py`
  - Connection helper + per-connection pragmas (WAL, busy_timeout, foreign_keys)
  - Schema migrations via `PRAGMA user_version`
  - Current schema includes:
    - `projects` (indexed columns + `payload_json`)
    - `agent_runs` (indexed columns + `payload_json`)
    - `agent_events` (indexed columns + `payload_json`)
    - `meta` key/value table
- `server/mypm/storage/sqlite_store.py`
  - Store classes:
    - `ProjectsStore`: list/get/create/patch/delete/reorder/batch_update + statistics
    - `AgentRunsStore`: create/get/list/patch
    - `AgentEventsStore`: append/exists/list
  - Design choice: keep full JSON payload in `payload_json` while indexing a small set of query fields

### Services

- `server/mypm/services/project_service.py`
  - Project CRUD and concurrency checks
  - Enforces optimistic concurrency with `updatedAt`/`ifUpdatedAt`
- `server/mypm/services/agent_service.py`
  - Agent runs CRUD (idempotent create)
- `server/mypm/services/deploy_service.py`
  - Starts a deploy job by running `deploy_pull_restart.sh`
  - Tracks job status via a state file and log file

### API Blueprints

- `server/mypm/api/meta.py`
  - `/api/health`: health check
  - `/api/meta`: capabilities/enums/auth requirements (used by UIs and agent clients)
- `server/mypm/api/projects.py`
  - `/api/projects`: list/create
  - `/api/projects/<id>`: get/put/patch/delete
  - `/api/projects/reorder`: persist sort order
  - `/api/projects/batch`: batch patch with per-item result statuses
- `server/mypm/api/stats.py`
  - `/api/stats`: project aggregation stats
- `server/mypm/api/agent.py`
  - `/api/agent/runs`: create/list
  - `/api/agent/runs/<id>`: get/patch
  - `/api/agent/events`: create/list
  - `/api/agent/actions`: semantic actions that update projects + write trace events
- `server/mypm/api/admin_ops.py`
  - `/api/admin/backup` (GET): export a consistent SQLite snapshot (download)
  - `/api/admin/restore` (POST): upload snapshot and atomically replace DB
  - `/api/admin/deploy` + `/deploy/status` + `/deploy/log`: optional server-side deploy trigger

## Frontend

### New UI (Vue 3)

- `frontend/src/`
  - `frontend/src/api/client.ts`: typed API client (projects/stats/agent/admin)
  - `frontend/src/stores/*`: state management (Pinia)
  - `frontend/src/components/*`: CRUD modals and ops modal
- Build outputs to `frontend/dist/` and is served at `/` when present

## Ops & Deployment

- `deploy_pull_restart.sh`
  - Linux-only helper for pulling code, installing deps, building frontend, and restarting the systemd service
  - Does NOT enable auto-backup by default (opt-in)
- `backup_db_snapshot.sh`
  - Creates a consistent SQLite snapshot using the Python backup API
  - Optional upload via env vars (`PM_BACKUP_UPLOAD_URL`, `PM_BACKUP_UPLOAD_TOKEN`, `PM_BACKUP_UPLOAD_METHOD`)
- `restore_db_snapshot.sh`
  - Replaces `pm.db` from a snapshot (manual/CLI flow)
- `setup_auto_backup.sh`
  - Installs `pilotdeck-backup.service` + `pilotdeck-backup.timer` and creates `/etc/pilotdeck/backup.env`
  - Opt-in scheduled backups with optional upload config

## Key Operational Flows

### Project Updates from Agents

1) Agent reads project (`GET /api/projects/<id>`) and captures `updatedAt`
2) Agent applies an update (`PATCH /api/projects/<id>` with `ifUpdatedAt`) or uses `/api/agent/actions`
3) Agent writes a trace event (`POST /api/agent/events`) and updates run status (`PATCH /api/agent/runs/<id>`)

### Backup Export and Restore

- Export: `GET /api/admin/backup` returns a consistent snapshot as a downloadable file
- Restore: `POST /api/admin/restore` accepts an uploaded snapshot and atomically replaces `data/pm.db`
