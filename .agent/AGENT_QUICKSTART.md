# Agent Quickstart

## Goal

Start fast with minimal tokens and one executable target.

## Read order (strict)

1. `.agent/HANDOFF.md`
2. `.agent/PLAN.yaml`
3. `.agent/ARCHITECTURE.md`
4. `.pilotdeck/status.yaml`
5. `docs/agent/AGENT_API.md`

## Execute rules

- Work only on the active step in `PLAN.yaml` (`doing`)
- Keep `PLAN.yaml` and `STATE.yaml` consistent
- Keep `.agent/STATE.yaml` and `.pilotdeck/status.yaml` sync metadata aligned
- Log major choices in `DECISIONS.md`
- Keep `MEMORY_INDEX.md` high-signal only
- Prefer semantic project mutations via `POST /api/agent/actions` when writing to PilotDeck
- On `409` conflict, run: fetch latest -> merge -> retry once -> record sync outcome

## No-time planning rule

- Do not plan by calendar date
- Advance by `cycle`, `step_id`, and `checkpoint`

## Human/Agent doc contract

- Canonical long-form docs are human-facing
- `.agent/` files are compact execution views
- Link to canonical docs instead of duplicating long text

## PilotDeck-specific runtime guardrails

- Primary remote identity: `project.id` in `.pilotdeck/status.yaml`
- Fallback identity: `project.name` only when ID is missing/invalid
- Required safety: preserve optimistic concurrency (`ifUpdatedAt`) for shared writes
- Always persist `last_run_id` / sync result for next-session recovery

## Session done checklist

1. Move completed acceptance items to done
2. Update blockers and next actions in `STATE.yaml`
3. Update `.pilotdeck/status.yaml` activity log and sync state when remote sync occurs
4. Rewrite `HANDOFF.md` with exact next steps
