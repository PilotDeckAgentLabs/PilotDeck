# Decisions (ADR-lite)

## D-0001

- Status: accepted
- Context: Multiple agents may write shared state.
- Decision: Use version-token optimistic concurrency with deterministic merge/retry.
- Consequences:
  - Pros: prevents silent overwrite
  - Cons: requires conflict handling path

## D-0002

- Status: accepted
- Context: Multiple audiences consume docs (humans and agents), causing duplication risk.
- Decision: Use canonical human-facing docs as source of truth and keep `.agent/` as compact execution view.
- Consequences:
  - Pros: lower drift, lower token cost, clearer ownership
  - Cons: requires discipline to keep links and contracts current

## D-0003

- Status: accepted
- Context: Agent operations need to access project endpoints without requiring web login sessions.
- Decision: Support dual-auth behavior for Projects API (session or agent token path).
- Consequences:
  - Pros: smoother agent automation and web compatibility
  - Cons: auth path testing matrix is broader

## D-0004

- Status: accepted
- Context: Local status files and remote project identity can diverge across repos.
- Decision: Resolve project identity with priority `project.id` -> `project.name` fallback; persist resolved ID in sync state.
- Consequences:
  - Pros: robust continuation and lower manual setup burden
  - Cons: ambiguous name collisions require explicit handling

## Template

Use this format for new records:

```text
## D-XXXX
- Status: proposed|accepted|deprecated
- Context: ...
- Decision: ...
- Consequences: ...
```
