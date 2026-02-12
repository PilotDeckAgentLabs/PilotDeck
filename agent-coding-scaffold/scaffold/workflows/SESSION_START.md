# Workflow: Session Start

## Objective

Start with minimal reading cost and a precise executable target.

## Required reads (in order)

1. `.agent/HANDOFF.md`
2. `.agent/PLAN.yaml`
3. `.agent/ARCHITECTURE.md`

## Required checks

1. Confirm active step exists in `PLAN.yaml`.
2. Confirm active step status is `doing` (or set one step to `doing`).
3. Confirm acceptance criteria are explicit and testable.
4. Confirm blockers in `STATE.yaml` are reflected in the execution strategy.

## Output of session start

- One active step
- One explicit goal for this session
- One verification path (tests/diagnostics/manual checks)
