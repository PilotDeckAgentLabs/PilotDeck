# Governance

## Scope

This project defines a neutral, production-ready scaffold standard for agent-driven software engineering workflows.

## Governance model

- Stewardship model: maintainer-led with public proposal process
- Decision mechanism: lightweight RFC + maintainer consensus
- Bias: backward-compatible evolution for templates and schemas

## Roles

- Maintainers
  - Review and merge changes
  - Own release readiness and compatibility policy
- Contributors
  - Propose improvements via issues/PRs
  - Provide migration notes for breaking changes
- Adopters
  - Use scaffold in real projects and report operational feedback

## Decision workflow

1. Open issue with problem statement and proposed change.
2. If structural/schema impact exists, submit RFC markdown in `governance/rfcs/`.
3. Collect feedback and revise.
4. Maintainers approve/reject with rationale.
5. If accepted, update docs/templates/schemas plus migration note.

## Compatibility policy

- Major: incompatible schema/workflow changes
- Minor: backward-compatible fields/templates/process additions
- Patch: fixes, clarity updates, typo/docs corrections

## Required for merging normative changes

- Update canonical docs impacted by change
- Update templates and schemas in lockstep
- Add migration guidance if behavior or schema changes
- Include at least one practical usage example

## Project values

- Clarity over cleverness
- Determinism over implicit behavior
- Auditability over convenience shortcuts
