# DOCUMENTATION CONTRADICTIONS

---

## Known Contradictions

### 1. Test Count in PROJECT_CONTINUATION.md

**File:** PROJECT_CONTINUATION.md
**Claim:** "1672 tests total, 1671 passing, 1 pre-existing seed test error"
**Reality:** 1,672 test methods exist in the codebase. The test count is accurate for the committed codebase. The Phase 1 tests (40 methods) are in the working tree and not yet committed.

**Classification:** DOCUMENTATION_DRIFT — will resolve when Phase 1 is committed.

### 2. OrderOffer Committed vs Working Tree

**File:** PROJECT_CONTINUATION.md
**Claim:** "Phase 1 implemented and verified (40 tests, 1671/1672 regression)"
**Reality:** Phase 1 implementation is in the working tree, not committed to git.

**Classification:** DOCUMENTATION_DRIFT — the implementation exists but hasn't been committed.

### 3. Migration Count

**File:** PROJECT_CONTINUATION.md
**Claim:** "Single migration: apps/orders/migrations/0008_orderoffer.py"
**Reality:** Correct for the working tree. The migration exists but is untracked.

**Classification:** Accurate but unstated that it's untracked.

---

## No Contradictions Found In

- Architecture decisions (ADMs are consistent)
- Workflow descriptions (match code)
- Permission model descriptions (match code)
- Financial system descriptions (match code)
- Test confidence matrix (matches actual test counts)

---

## Old Documentation Status

| Category | Count | Status |
|----------|-------|--------|
| Root-level reports | 6 files | Historical — retained for traceability |
| Sprint verification docs | 7 files | Historical — sprint-specific |
| Module specifications | 256 files | Historical — generic framework, not project-specific |
| docs/architecture | 16 files | Archived 2026-07-14 (`_archive/documentation/20260714-124624/`) |
| docs/adr | 11 files | Archived 2026-07-14 — active decisions summarized in `current/ACTIVE_ARCHITECTURE_DECISIONS.md` |
| mimo change | 10 files | Archived 2026-07-14 — active history continues in `traceability/` |

---

## Resolution Update — 2026-07-14 (verified at HEAD ce3b30e)

Contradictions 1–3 above are RESOLVED: OrderOffer Phase 1 (model, migration
`orders/0008_orderoffer.py`, admin, 40 tests) was committed in `ce3b30e`.
The working tree is clean. Test-count and migration statements now describe
committed code.

New contradictions found and fixed by the 2026-07-14 documentation sync:

1. Root `AI_START_HERE.md`, `DOCUMENTATION_RULES.md`, `PROJECT_CONTINUATION.md`,
   `NEXT_TASK.md`, `project docs/01_PROJECT_RULES.md`,
   `project docs/DOCUMENTATION_RULES.md`, `registry/DOCUMENTATION_REGISTRY.md`,
   and `registry/SUPERSESSION_MAP.md` referenced `canonical docs/` and
   `mimo change/` — paths that no longer exist (content reorganized into
   `project docs/`, originals archived). All active references removed.
2. Root `README.md` pointed to `docs/architecture/*` files that were archived
   under `_archive/documentation/20260714-124624/`. Now points to
   `project docs/00_START_HERE.md`.
3. One prior claim in this audit corrected by execution evidence: the seed
   test failure is NOT only a full-regression concurrency effect — on
   2026-07-14 it failed 1/10 runs in isolation (random in-run order_number
   collision). See `quality/COMPLETION_BACKLOG.md` BG-002.
