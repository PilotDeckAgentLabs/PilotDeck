# Contributing

Thanks for contributing to Agent Coding Scaffold.

## Contribution scope

We accept contributions in these areas:

- Core scaffold templates under `scaffold/templates/`
- Schema definitions under `scaffold/schemas/`
- Workflow specifications under `scaffold/workflows/`
- Documentation and examples under `docs/`
- Bootstrap/validation tooling under `scripts/`

## Before opening a PR

1. Open an issue for substantial behavior/schema changes.
2. For normative changes, add or update an RFC in `governance/rfcs/`.
3. Check if your change is breaking (major), additive (minor), or fix (patch).

## Local checks

Run from repository root:

```bash
python -m py_compile scripts/init_scaffold.py scripts/validate_scaffold.py
python scripts/init_scaffold.py --target _smoke --project-id proj-smoke --project-name "Smoke Project" --repo "github.com/example/smoke" --force
python scripts/validate_scaffold.py --target _smoke
```

Then remove `_smoke`.

## Pull request requirements

- Keep scope focused and minimal.
- Update related docs/templates/schemas in lockstep.
- Add migration notes for breaking changes.
- Update `release/CHANGELOG.md`.
- Include rationale and tradeoffs in PR description.

## Style guidance

- Prefer explicit, deterministic rules over implicit behavior.
- Keep templates easy to read and operationally practical.
- Avoid platform-specific coupling in core artifacts.

## Commit message guidance

Use clear, intent-first messages, for example:

- `feat: add plan schema v1 with step dependency rules`
- `fix: align status template with state schema`
- `docs: clarify session-end handoff requirements`
