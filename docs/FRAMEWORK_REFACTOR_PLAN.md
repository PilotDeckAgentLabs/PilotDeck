# Framework Refactor Plan (2026)

This document captures the agreed architecture direction and a staged refactor plan.

Scope: improve maintainability/readability/extensibility as the project grows (AgentOps, richer APIs, UI expansion).

## Goals

- Prevent "giant script" growth (current hotspots: `server/api_server.py`, `web/js/app.js`, `web/css/style.css`).
- Establish clear module boundaries (API layer vs business vs storage).
- Make Agent-first APIs robust (validation, idempotency, audit traceability, versioning).
- Modernize frontend to Vue 3 + Vite + TypeScript for long-term UI iteration speed.
- Keep deployment simple (local-first) and preserve data compatibility.

## Non-Goals (for this refactor)

- Not redesigning product features.
- Not switching to enterprise infra (K8s, complex auth, etc.).
- Not forcing immediate DB migration; keep JSON/JSONL storage initially.

## Current State (Baseline)

- Backend: Flask + Flask-CORS, JSON file storage (`data/projects.json`), JSONL events, JSON runs.
- Frontend: vanilla HTML/CSS/JS (monolithic files), served as static assets by backend.
- Ops: shell scripts for deploy/pull/push/backup; some admin endpoints.

## Target Architecture (End State)

### Frontend (Selected)

- Vue 3 + Vite + TypeScript
- State: Pinia
- Routing: Vue Router (even if single page today, keep future-proof)
- API client: generated from OpenAPI (preferred) or typed hand-written client during migration
- Styling:
  - Keep existing design tokens (CSS variables)
  - Move to `src/styles/tokens.css` + `src/styles/base.css` + component-scoped styles

### Backend (Recommended Evolution)

Phase 1 (low-risk): keep Flask, but split into modules + services + storage interfaces.
Phase 2 (high ROI): migrate API to FastAPI + Pydantic for:

- Request/response validation
- Automatic OpenAPI
- Better agent/tooling integration (typed clients, schema-driven skills)

### Storage (Evolvable)

Start: JSON/JSONL with atomic writes + file locks.
Later (optional): SQLite (transactions + indexing) while preserving JSON import/export for Git-based audit.

## Key Design Principles

### 1) Layering

- API Layer: HTTP routing, auth, input parsing, response mapping
- Service/Use-Case Layer: business workflows (apply actions, write events, reorder, etc.)
- Storage Layer: persistence and migration/normalization

Rule: API layer must not "know" file formats; storage layer must not "know" HTTP.

### 2) Domain-Driven Modules

Split by domain area:

- `projects`
- `agent` (actions/events/runs)
- `stats`
- `ops/admin`

### 3) Agent-Safe Operations

- Prefer semantic actions endpoint(s) over raw patching.
- Record per-project execution trace (events) with run grouping.
- Idempotency by action/event id.
- Optional optimistic concurrency (`ifUpdatedAt`) for multi-agent parallel writes.

### 4) Backward Compatibility

- `projects.json` / `agent_runs.json`: fill missing fields with defaults and write back.
- `agent_events.jsonl`: normalize on read only (do not rewrite history).

## Proposed Repository Layout

### Backend (target)

```
server/
  mypm/
    __init__.py
    app.py               # create_app()/build_app()
    config.py            # env vars, file paths, tokens
    api/
      __init__.py
      meta.py            # /api/meta /api/health
      projects.py        # /api/projects/*
      agent.py           # /api/agent/*
      stats.py           # /api/stats
      admin_ops.py       # /api/admin/*
    domain/
      __init__.py
      enums.py           # status/priority
      models.py          # Project/AgentEvent/AgentRun/AgentAction (Pydantic-ready)
      errors.py          # typed errors
    services/
      __init__.py
      project_service.py
      agent_service.py
    storage/
      __init__.py
      locks.py           # cross-process file lock
      atomic.py          # tmp+replace JSON write
      projects_json.py
      agent_events_jsonl.py
      agent_runs_json.py
  main.py                # entrypoint
```

### Frontend (target)

```
frontend/
  index.html
  vite.config.ts
  tsconfig.json
  src/
    main.ts
    App.vue
    pages/
      ProjectsPage.vue
      ProjectDetailModal.vue
    components/
      ...
    stores/
      projects.ts
      agent.ts
    api/
      client.ts          # typed fetch wrapper
      generated/         # OpenAPI generated client (later)
    styles/
      tokens.css
      base.css
```

## Staged Migration Plan

### Phase 0: Safety Baseline (1-2 sessions)

- Add a dedicated architecture doc (this file) and keep it updated.
- Add minimal smoke tests for critical API endpoints.
- Introduce consistent formatting + linting (Python + TS) before heavy refactors.

Deliverable:
- Documented plan + minimal verification commands.

### Phase 1: Backend Refactor Without Framework Switch (Flask stays) (2-5 sessions)

- Split `server/api_server.py` into modules (Blueprints) by domain.
- Extract business logic into `services/`.
- Extract persistence into `storage/` with interfaces.
- Ensure atomic writes + file locks are consistently applied.

Deliverables:
- Same endpoints, same behavior, but smaller files.
- Storage layer testable in isolation.

### Phase 2: Frontend Modernization (Vue 3 + Vite + TS) (3-8 sessions)

- Create `frontend/` Vite app.
- Implement core flows:
  - Project list (card/list view)
  - Project detail (edit + Agent timeline)
- Keep backend serving old `web/` until new UI is feature-complete.
- Add a new mount path (example): `/app` serves new frontend build, while `/` keeps old UI during transition.

Deliverables:
- New UI running in dev mode and build mode.
- Feature parity for essential operations.

### Phase 3: Backend Switch to FastAPI (optional but recommended) (3-6 sessions)

- Introduce Pydantic models as the single schema source.
- Migrate endpoints gradually:
  - Start with `/api/agent/*` (most schema-sensitive)
  - Then `/api/projects/*`, `/api/stats`
- Generate OpenAPI and start using generated TS client in frontend.

Deliverables:
- OpenAPI available at `/openapi.json`.
- Frontend uses typed client.

### Phase 4: Storage Upgrade to SQLite (optional, when needed) (variable)

Trigger criteria:
- Concurrent multi-agent writes become common.
- Need fast queries on events/runs.
- Need stronger guarantees (transactions).

Deliverables:
- SQLite backend with migrations.
- JSON import/export retained for Git-based audit.

## Compatibility & Versioning Strategy

- Add `/api/v1` as stable prefix (keep `/api` as alias during transition).
- Maintain response envelope: `{ success, data, error }`.
- Enforce schema normalization:
  - projects/runs: normalize + persist
  - events: normalize on read only

## Testing & Tooling (Minimum Set)

Backend (Python):
- Add `pytest` for API smoke tests (test client) and storage tests.
- Add `ruff` + `black` (or ruff-format) for consistent style.
- Optional: `mypy` once models stabilize.

Frontend (TS/Vue):
- `eslint` + `prettier`
- `vitest` for store/service tests
- `playwright` later for end-to-end (optional)

## Deployment Considerations

- Keep current shell scripts working during Phase 1-2.
- When Vue build is adopted:
  - Serve built assets from backend (`frontend/dist`) or via a small static server.
- When FastAPI is adopted:
  - `uvicorn` run under systemd (similar operational model).

## Acceptance Criteria

The refactor is considered successful when:

- No single backend file exceeds ~400-600 lines (rule of thumb), and responsibilities are separated.
- Frontend is componentized (no monolithic `app.js`), state is centralized (Pinia), and API client is typed.
- Agent APIs remain stable and documented; events provide per-project traceability.
- Backward compatibility is preserved: older data files load without manual edits.
- Basic smoke tests exist and run clean.

## Immediate Next Steps (Execution Order)

1) Decide whether to keep Flask through Phase 2 (recommended) or switch to FastAPI earlier.
2) Create the `frontend/` Vite + Vue + TS skeleton.
3) Define Pydantic-style models (even if Flask stays temporarily) to prepare for OpenAPI.
