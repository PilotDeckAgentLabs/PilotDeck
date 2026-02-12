# Memory Index

Store only high-signal memory for cross-session continuity.

## Entry format

- ID: `M-0001`
- Type: `decision|bugfix|discovery|risk|rule`
- Summary: short actionable statement
- Affects: modules/domains impacted
- References: file paths

## Entries

- ID: `M-0001`
  - Type: `decision`
  - Summary: "Use optimistic concurrency for all shared-state writes"
  - Affects: `api`, `sync`
  - References: `docs/ARCHITECTURE.md`, `.agent/DECISIONS.md`
