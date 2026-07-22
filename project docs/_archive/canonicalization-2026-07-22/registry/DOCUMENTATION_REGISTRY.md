# DOCUMENTATION REGISTRY

**Updated:** 2026-07-14 (documentation sync at HEAD ce3b30e)
**Repository:** taasisatSeniorNew
**Purpose:** Authoritative registry of active and archived Markdown documentation.

## Active documentation

All active project documentation lives under **`project docs/`**:

- `project docs/00_START_HERE.md` — entry point and reading order
- `project docs/01_PROJECT_RULES.md` — source-of-truth order and rules
- `project docs/02_PROJECT_CONTINUATION.md` — current project state
- `project docs/03_NEXT_TASK.md` — immediate next objective
- `project docs/IMPLEMENTATION_ROADMAP.md` — the single active implementation order
- `project docs/DOCUMENTATION_RULES.md` — documentation governance
- `project docs/current/` — 9 documents describing the current implemented system
- `project docs/quality/` — 5 documents: backlog, risks, duplication, legacy, test confidence
- `project docs/audit/` — 12 forensic audit reports
- `project docs/traceability/` — 6 append-only history files
- `project docs/registry/` — this registry, supersession map, evidence and method

Root-level pointer files (no authoritative content of their own):

- `README.md` — repository overview, points to `project docs/00_START_HERE.md`
- `AI_START_HERE.md` — AI entry point, points to `project docs/`
- `DOCUMENTATION_RULES.md` — points to `project docs/DOCUMENTATION_RULES.md`
- `PROJECT_CONTINUATION.md` — points to `project docs/02_PROJECT_CONTINUATION.md`
- `NEXT_TASK.md` — points to `project docs/03_NEXT_TASK.md`

Developer/technical documentation that remains active in place:

- `src/RUN_NATIVE_NO_VENV.md`
- `src/tests/visual/README.md`
- `src/ui/components/illustrations/README.md`
- `src/ui/docs/` (COMPONENT_GUIDE, DESIGN_SYSTEM, RTL_GUIDE, THEME_ENGINE, UI_ARCHITECTURE)
- `src/ui/fonts/README.md`

## Archived documentation

`canonical docs/` and `mimo change/` are **not** active paths. Their content
was reorganized into `project docs/` and the original files were moved,
without deletion, to:

- `_archive/documentation/20260714-124624/`

The complete move list is recorded in:

- `_documentation_cleanup/moved-files-20260714-124624.csv`

Archived files must not be used as the current source of truth unless a
specific historical decision must be investigated.
