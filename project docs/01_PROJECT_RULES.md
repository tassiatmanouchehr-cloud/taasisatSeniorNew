# PROJECT RULES

## Source-of-truth order

1. Current source code, migrations, and tests
2. `project docs/current/PROJECT_BASELINE.md` — the canonical, always-current
   project snapshot (completed/partial/not-started phases, implementation
   matrix, risks, technical debt, milestones, production-readiness verdict)
3. `project docs/02_PROJECT_CONTINUATION.md`
4. `project docs/03_NEXT_TASK.md`
5. `project docs/IMPLEMENTATION_ROADMAP.md` and `project docs/current/`
6. Active traceability files under `project docs/traceability/`
7. Archived documentation (`_archive/`) only for historical investigation

Point-in-time assessments that `PROJECT_BASELINE.md` is derived from live under
`project docs/assessments/`, dated and immutable — consult them for the full
evidence behind a baseline, never as a substitute for the current baseline
itself.

## Rules

- Do not treat archived Markdown files as current requirements.
- Do not restore an archived design merely because it exists in history.
- Update affected documents under `project docs/` whenever behavior changes.
- Append change evidence to `project docs/traceability/` files.
- Do not create new root-level reports unless explicitly approved.
- New long-form project documentation belongs under `project docs/`.
- Temporary reviews and forensic outputs belong under `_archive/` after review.
- Repository code overrides documentation when they conflict; document the drift.
- **Every significant implementation milestone or Epic completion must conclude
  with, in order: (1) a repository assessment verified against code, not
  assumed from prior documentation; (2) documentation synchronization of every
  active document the milestone changed; (3) an in-place update to
  `project docs/current/PROJECT_BASELINE.md`, with the assessment that produced
  it filed as a new, immutable, dated file under `project docs/assessments/`;
  (4) a re-derived next-milestone entry in `PROJECT_BASELINE.md`, never carried
  forward by default numbering alone.** See `PROJECT_BASELINE.md` §18 for the
  full rule.
