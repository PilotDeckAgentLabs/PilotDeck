# Agent Coding Scaffold

A production-ready, platform-agnostic scaffold for AI-agent software engineering.

This project provides a reusable framework for end-to-end agent-driven delivery:

- Plan
- Design
- Architecture
- Implementation
- Testing
- Validation
- Handoff

The scaffold is optimized for cross-session continuity and token efficiency.

## Project governance and release

- Governance: `governance/GOVERNANCE.md`
- Maintainers: `governance/MAINTAINERS.md`
- Release process: `release/RELEASE.md`
- Changelog: `release/CHANGELOG.md`
- Contribution guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`

## Why this exists

Most agent sessions restart from scratch, re-reading large codebases and re-deriving context.
This scaffold uses structured local artifacts so each new session starts from a compact, high-signal state.

## What you get

- A standard `.agent/` workspace for machine-oriented project memory
- Human-friendly docs with clear ownership and update rules
- A no-calendar plan model (`cycle`, `step`, `checkpoint`) that avoids wall-clock coupling
- Session workflows for start, execution loop, and end
- Governance and release baseline for standard-style OSS maintenance

## Repository layout

```text
agent-coding-scaffold/
  docs/
    VISION.md
    POSITIONING.md
    FEATURES.md
    FRAMEWORK.md
    USAGE.md
  scaffold/
    templates/
      .agent/
        PROJECT.md
        ARCHITECTURE.md
        PLAN.yaml
        STATE.yaml
        MEMORY_INDEX.md
        DECISIONS.md
        HANDOFF.md
      status.yaml
    schemas/
      plan.schema.yaml
      state.schema.yaml
      status.schema.yaml
    workflows/
      SESSION_START.md
      EXECUTION_LOOP.md
      SESSION_END.md
  governance/
    GOVERNANCE.md
    MAINTAINERS.md
    CODE_OF_CONDUCT.md
  release/
    RELEASE.md
    CHANGELOG.md
  scripts/
    init_scaffold.py
    validate_scaffold.py
```

## Quick start

1. Copy this folder into your target project root.
2. Run:

```bash
python agent-coding-scaffold/scripts/init_scaffold.py --target . --project-id proj-example --project-name "Example Project" --repo "github.com/acme/example"
```

Optional validation:

```bash
python agent-coding-scaffold/scripts/validate_scaffold.py --target .
```

3. Start each session by reading, in order:
   1) `.agent/HANDOFF.md`
   2) `.agent/PLAN.yaml`
   3) `.agent/ARCHITECTURE.md`
4. Work from `current_step_id` and update `.agent/STATE.yaml` + `.agent/PLAN.yaml` continuously.
5. End each session by rewriting `.agent/HANDOFF.md`.

See `docs/USAGE.md` for full workflow.
