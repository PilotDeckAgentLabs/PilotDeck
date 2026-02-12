# Release Process

## Versioning

This project follows semantic versioning:

- MAJOR: breaking schema/workflow changes
- MINOR: backward-compatible additions/improvements
- PATCH: fixes and clarifications

## Release checklist

1. Confirm docs/templates/schemas are consistent.
2. Update `release/CHANGELOG.md`.
3. Validate scaffold bootstrap scripts.
4. Run smoke initialization in a clean folder.
5. Tag release (`vX.Y.Z`).
6. Publish release notes with migration impact.

## Normative change gate

Any change to these files is normative and requires explicit changelog entry:

- `scaffold/templates/.agent/*`
- `scaffold/templates/status.yaml`
- `scaffold/schemas/*.yaml`
- `scaffold/workflows/*.md`

## Migration notes

For any breaking change, release notes must include:

- What changed
- Why it changed
- How to migrate existing projects
- Compatibility fallback strategy
