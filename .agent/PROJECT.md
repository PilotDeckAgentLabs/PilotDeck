# Project Charter

## Identity

- Project ID: `proj-46e1c1d8`
- Project Name: `PilotDeck`
- Repository: `github.com/PilotDeckAgentLabs/PilotDeck`

## Objective

Deliver a self-hosted ProjectOps x AgentOps console where humans and agents can advance project execution with auditable runs/events/actions, conflict-safe updates, and cost observability.

## Scope

### In scope

- Backend API and services (`server/mypm/*`)
- Frontend product UI (`frontend/src/*`)
- Agent integration contracts and workflows (`docs/agent/*`, `pilotdeck-skill/*`)
- Project/status sync model (`.pilotdeck/status.yaml`, `docs/product/*`)

### Out of scope

- Managed cloud hosting platform
- Multi-tenant org/billing platform
- Replacing GitHub/Jira as full project suite

## Constraints

- Local-first architecture (SQLite, minimal external dependencies)
- Concurrency safety via `updatedAt + ifUpdatedAt`
- Agent API compatibility and deterministic behavior
- Backward compatibility for status file schema where practical

## Quality bar

- Behavior changes include verification evidence (tests/build/diagnostics)
- API contract changes require doc updates in `docs/agent/AGENT_API.md`
- Status schema changes require template sync in `docs/product/PROJECT_STATUS_TEMPLATE.md`
- Security-sensitive flows preserve token boundary (`PM_AGENT_TOKEN`, `PM_ADMIN_TOKEN`)

## Glossary

- ProjectOps: project status/progress/priority orchestration on `projects`
- AgentOps: agent run/event/action lifecycle with audit trail
- Run: one agent work session (`/api/agent/runs`)
- Event: append-only audit record (`/api/agent/events`)
- Action: semantic mutation with optional project update (`/api/agent/actions`)
