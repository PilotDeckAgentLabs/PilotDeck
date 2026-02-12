# Architecture Summary

## System map

```text
Web UI / Agent Client
  -> Flask Blueprints (server/mypm/api/*)
  -> Services (server/mypm/services/*)
  -> Stores (server/mypm/storage/*)
  -> SQLite (data/pm.db)
```

## Module responsibilities

- `server/mypm/api/projects.py`: project CRUD, optimistic concurrency check
- `server/mypm/api/agent.py`: run/event/action endpoints for auditable agent workflows
- `server/mypm/services/project_service.py`: project mutation and validation orchestration
- `server/mypm/services/agent_service.py`: run/event/action business logic
- `server/mypm/storage/sqlite_store.py`: persistence and indexed query paths
- `frontend/src/stores/*`: UI state management for projects and agent timelines

## Data flow

### Web flow

1. UI triggers API call through frontend API client.
2. Flask blueprint validates/authenticates request.
3. Service layer applies domain rules and conflict checks.
4. Storage layer writes indexed columns and payload JSON.

### Agent flow

1. Agent creates/updates run (`/api/agent/runs`).
2. Agent mutates project via semantic actions (`/api/agent/actions`) or patch.
3. Agent appends timeline events (`/api/agent/events`).
4. Agent finalizes run and writes local sync state.

## Key invariants

- Project writes in shared contexts use `ifUpdatedAt` for optimistic locking.
- `agent_events` are append-only; audit history is never rewritten.
- `POST /api/agent/actions` must preserve idempotent behavior by action identity.
- Project identity resolution uses `project.id` first, then `project.name` fallback.

## Failure handling

- 409 conflict: fetch latest project, merge deterministically, retry once.
- Partial batch failures: preserve per-op status and do not hide failed ops.
- Sync failures: persist error details to local status/sync state for next session recovery.

## References

- `docs/ARCHITECTURE.md`
- `server/docs/ARCHITECTURE.md`
- `docs/agent/AGENT_API.md`
- `docs/product/PROJECT_STATUS_TEMPLATE.md`
