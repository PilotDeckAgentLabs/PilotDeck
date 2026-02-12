# Workflow: Execution Loop

## Rules

1. Work only on the active step.
2. Keep changes minimal and aligned with existing code patterns.
3. Record decisions that change architecture, behavior, or contracts.

## Loop

1. Implement one atomic increment.
2. Verify increment (tests/diagnostics).
3. Update `.agent/STATE.yaml` and `.agent/MEMORY_INDEX.md` if new high-signal facts appear.
4. If acceptance criteria are satisfied, mark step `done` and move next dependency-ready step to `doing`.

## Conflict handling

- If external sync returns conflict (`409`-like):
  1. fetch latest remote state
  2. merge deterministically
  3. retry once
  4. log result in local sync state
