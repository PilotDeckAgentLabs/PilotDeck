# Workflow: Session End

## Required updates

1. `.agent/PLAN.yaml`
   - statuses reflect actual completion state
2. `.agent/STATE.yaml`
   - blockers, next actions, sync outcome are current
3. `.agent/HANDOFF.md`
   - rewritten for immediate next-session execution

## Optional external sync

If using an adapter:

1. Resolve project identity (`id` first, then name fallback).
2. Start/update run context.
3. Append events and apply semantic actions.
4. Finalize run status.
5. Persist remote IDs and errors in local state.

## Completion gate

- Plan and state are consistent
- Handoff is concrete and actionable
- No unresolved hidden assumptions
