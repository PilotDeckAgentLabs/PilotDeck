# Framework

## Mental model

The scaffold uses a layered context model:

1. Stable layer (changes slowly)
   - Project charter, architecture, constraints
2. Active layer (changes per cycle)
   - Current plan, current step, blockers, next actions
3. Event layer (changes per session)
   - Observations, decisions, activity logs, sync metadata

## Canonical artifacts

- `.agent/PROJECT.md`: project mission, scope, constraints, glossary
- `.agent/ARCHITECTURE.md`: module map, data flow, critical invariants
- `.agent/PLAN.yaml`: executable plan with step statuses
- `.agent/STATE.yaml`: current execution state snapshot
- `.agent/MEMORY_INDEX.md`: compressed high-signal memory entries
- `.agent/DECISIONS.md`: ADR-style record of major decisions
- `.agent/HANDOFF.md`: next-session launch brief

## State model

### Project lifecycle

- `planning`
- `in-progress`
- `paused`
- `completed`
- `cancelled`

### Plan step status

- `todo`
- `doing`
- `done`
- `blocked`

### Run status

- `running`
- `success`
- `failed`
- `cancelled`

## Session protocol

1. Session start
   - Read `HANDOFF.md`, `PLAN.yaml`, `ARCHITECTURE.md`
   - Confirm current step and acceptance criteria
2. Execution loop
   - Implement only the active step
   - Update state and decision logs continuously
3. Session end
   - Update plan progress and unresolved blockers
   - Rewrite `HANDOFF.md` with exact next actions

## Integration boundary

This scaffold is integration-agnostic by default.

If you integrate with external systems later, keep integration code outside core templates and preserve local `.agent` files as the canonical execution memory.

## Reliability rules

- On concurrency conflict (`409`-like): fetch latest, merge deterministically, retry once
- Keep idempotency keys stable per logical operation
- Never mutate plan and state in contradictory ways
- Persist run/event identifiers back into local state
