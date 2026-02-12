# Usage

## 1) Initialize scaffold in a project

From your target project root:

```bash
python agent-coding-scaffold/scripts/init_scaffold.py --target . --project-id proj-example --project-name "Example Project" --repo "github.com/acme/example"
```

This creates:

- `.agent/` workspace files
- `status.yaml` integration file

## 2) Start every session the same way

Read in this order:

1. `.agent/HANDOFF.md`
2. `.agent/PLAN.yaml`
3. `.agent/ARCHITECTURE.md`

Then set one active step in `PLAN.yaml` (`doing`) and begin work.

## 3) Execution loop

During work:

- Update `.agent/STATE.yaml` whenever context changes materially
- Log key decisions in `.agent/DECISIONS.md`
- Add only high-signal entries to `.agent/MEMORY_INDEX.md`
- Move completed steps from `doing` to `done` immediately

## 4) Session end ritual

Before ending:

- Ensure `PLAN.yaml` and `STATE.yaml` agree
- Write blockers and exact next actions
- Rewrite `.agent/HANDOFF.md` for the next session

## 5) Optional external sync (later phase)

Initial scaffold is intentionally platform-neutral and does not ship adapters.

If your organization adds integration later, keep it as a separate extension layer and do not mutate core scaffold templates.

## Operational guidance

- Avoid time-based project planning; prefer `cycle`, `step_id`, and `checkpoint` progression.
- Keep human docs concise and canonical; keep agent docs structured and executable.
- Do not duplicate full architecture narratives in handoff files.
