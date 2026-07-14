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
| docs/architecture | 16 files | Partially valid — some info superseded by canonical docs |
| docs/adr | 11 files | Active — ADMs are binding decisions |
| mimo change | 10 files | Active — append-only change history |
