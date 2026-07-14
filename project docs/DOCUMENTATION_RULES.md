# DOCUMENTATION RULES

## Source-of-truth order

1. Current source code, migrations, and tests
2. `project docs/02_PROJECT_CONTINUATION.md`
3. `project docs/03_NEXT_TASK.md`
4. `project docs/IMPLEMENTATION_ROADMAP.md` and `project docs/current/`
5. Active traceability files under `project docs/traceability/`
6. Archived documentation (`_archive/`) only for historical investigation

## Rules

- Do not treat archived Markdown files as current requirements.
- Do not restore an archived design merely because it exists in history.
- Update affected documents under `project docs/` whenever behavior changes.
- Append change evidence to `project docs/traceability/` files.
- Do not create new root-level reports unless explicitly approved.
- New long-form project documentation belongs under `project docs/`.
- Temporary reviews and forensic outputs belong under `_archive/` after review.
- Repository code overrides documentation when they conflict; document the drift.
