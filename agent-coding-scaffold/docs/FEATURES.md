# Features

## Core capabilities

1. Session continuity by design
   - Structured handoff and state files reduce re-context overhead.
2. Plan-first execution
   - Work advances via explicit steps, dependencies, and acceptance criteria.
3. Decision traceability
   - Architecture and tradeoff decisions are logged in a dedicated decision record.
4. Conflict-safe sync model
   - Supports optimistic concurrency flows and deterministic retries.
5. Integration-agnostic core
   - Core scaffold works without any platform-specific adapter.

## Production defaults

- Schema versioning for backward compatibility
- Explicit lifecycle/task state enums
- Machine-readable YAML + human-readable markdown surfaces
- Deterministic session start/end routines
- Minimal required fields with safe defaults

## Token-efficiency strategies

- Progressive disclosure: read short index docs first
- Memory index: store only high-signal observations
- No full transcript replay as default
- Link-based deep dives instead of duplicated long text
