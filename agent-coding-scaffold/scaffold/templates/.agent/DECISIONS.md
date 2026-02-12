# Decisions (ADR-lite)

## D-0001

- Status: accepted
- Context: Multiple agents may write shared state.
- Decision: Use version-token optimistic concurrency with deterministic merge/retry.
- Consequences:
  - Pros: prevents silent overwrite
  - Cons: requires conflict handling path

## Template

Use this format for new records:

```text
## D-XXXX
- Status: proposed|accepted|deprecated
- Context: ...
- Decision: ...
- Consequences: ...
```
