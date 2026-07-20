# PROJECT DOCUMENTATION — START HERE

This directory is the active documentation source for ChatGPT and Claude Code.

## Required reading order

1. `01_PROJECT_RULES.md`
2. `current/PROJECT_BASELINE.md` — the canonical current-state snapshot: what's
   done, partial, not started, current risks/debt, current milestone, next
   milestone, production-readiness verdict. Read this before anything else
   that claims to describe "where the project is."
3. `02_PROJECT_CONTINUATION.md`
4. `03_NEXT_TASK.md`
5. `IMPLEMENTATION_ROADMAP.md` — the active implementation order
6. Relevant document under `current/`
7. Related risks under `quality/`
8. Related audit report under `audit/`
9. Current repository code, migrations, and tests

## Directory roles

- `current/PROJECT_BASELINE.md` — the single canonical current-state snapshot
- `assessments/` — dated, immutable, point-in-time repository assessments that
  each baseline update in `current/PROJECT_BASELINE.md` is derived from
- `IMPLEMENTATION_ROADMAP.md` — the single active implementation order
- `current/` — current implemented system
- `quality/` — risks, tests, duplication, backlog
- `audit/` — deep forensic findings
- `traceability/` — implementation and test history
- `registry/` — documentation ownership and evidence

Documents under `_archive/` are historical and must not be used as current authority.

Current source code, migrations, and tests remain the ultimate source of truth.
