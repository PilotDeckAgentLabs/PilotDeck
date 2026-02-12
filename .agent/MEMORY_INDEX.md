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

- ID: `M-0002`
  - Type: `decision`
  - Summary: "Use project.id as primary identity, fallback to project.name when resolving remote project"
  - Affects: `status-sync`, `agent-api`
  - References: `docs/agent/AGENT_API.md`, `docs/product/PROJECT_STATUS_TEMPLATE.md`

- ID: `M-0003`
  - Type: `discovery`
  - Summary: "Project names are not guaranteed unique; ambiguous name matches require explicit ID selection"
  - Affects: `sync-reliability`
  - References: `docs/agent/PILOTDECK_SKILL.md`, `PILOTDECK_SKILL_STATUS_OPTIMIZATION.md`

- ID: `M-0004`
  - Type: `decision`
  - Summary: "Projects API supports both web session and agent token authentication via dual-auth path"
  - Affects: `api-auth`, `agent-integration`
  - References: `README.md`, `server/mypm/api/projects.py`

- ID: `M-0005`
  - Type: `rule`
  - Summary: "Maintain single-source canonical docs with agent-specific execution view in .agent"
  - Affects: `docs-governance`
  - References: `docs/README.md`, `.agent/AGENT_QUICKSTART.md`
