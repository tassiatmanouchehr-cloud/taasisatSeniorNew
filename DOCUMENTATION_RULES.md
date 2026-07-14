# DOCUMENTATION RULES

## Source-of-truth order

1. Current source code, migrations, and tests
2. `PROJECT_CONTINUATION.md`
3. `NEXT_TASK.md`
4. `canonical docs/`
5. Active traceability files under `mimo change/`
6. Archived documentation only for historical investigation

## Rules

- Do not treat archived Markdown files as current requirements.
- Do not restore an archived design merely because it exists in history.
- Update affected canonical documents whenever behavior changes.
- Append change evidence to the active traceability files.
- Do not create new root-level reports unless explicitly approved.
- New long-form project documentation belongs under `canonical docs/`.
- Temporary reviews and forensic outputs belong under `_archive/` after review.
- Repository code overrides documentation when they conflict; document the drift.
