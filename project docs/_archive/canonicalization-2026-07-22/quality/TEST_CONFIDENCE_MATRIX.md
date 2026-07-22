# TEST CONFIDENCE MATRIX

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f (per-app table below);
partial update 2026-07-15 (phase1-registration-manual-verification) — only the
`accounts`/`admin_portal` rows and grand-total method count were re-verified;
partial update 2026-07-15 (phase2-caregiver-professional-profile-foundation) — only
`accounts`/`provider_portal`/`public_site` rows and grand-total method count re-verified;
partial update 2026-07-15 (PR #6 BG-022 remediation) — only the `public_site` row and
grand-total file/method counts re-verified;
partial update 2026-07-15 (Sprint 2.2 — Caregiver Gallery and Media Portfolio) — only
`accounts`/`provider_portal`/`public_site` rows and grand-total file/method counts
re-verified;
partial update 2026-07-15 (PR #7 file-lifecycle/image-safety remediation) — only the
`accounts` row (test methods, +2 classes in the existing gallery test file, no new file)
and grand-total method count re-verified;
partial update 2026-07-15 (Sprint 2.3 — Credentials, Skills, Experience, Highlights) — only
`accounts`/`provider_portal`/`public_site` rows and grand-total method count re-verified;
no new test file this sprint (all additions inside existing files);
partial update 2026-07-15 (Sprint 2.4 — Caregiver Availability and Working Schedule) — only
`availability`/`provider_portal`/`public_site` rows and grand-total method count
re-verified; no new test file this sprint (all additions inside existing files);
partial update 2026-07-15 (PR #9 review — availability mutation concurrency remediation) —
only the `availability` row (test methods, concurrency column, +1 new test file:
`test_concurrency.py`) and grand-total file/method counts re-verified;
partial update 2026-07-15 (Sprint 2.5 — Caregiver Professional Dashboard) — only
`orders`/`finance`/`reviews`/`provider_portal` rows and grand-total file/method counts
re-verified (+3 new test files: `test_supplier_queries.py`, `test_beneficiary_queries.py`,
`test_professional_dashboard.py`);
partial update 2026-07-15 (Sprint 2.6 — Public Profile Finalization and Phase 2
Acceptance) — only the `public_site` row and grand-total file/method counts re-verified
(+1 new test file: `test_phase2_acceptance.py`, 5 tests); one pre-existing test in
`accounts.tests.test_caregiver_professional_profile` fixed (no new test method, existing
count unchanged);
partial update 2026-07-15 (Sprint 2.6 PR #11 review — resolve the KL-012
query-performance blocker) — only the `public_site` row and grand-total method count
re-verified (`test_phase2_acceptance.py`'s query-budget test class expanded from 3 to 15
methods, +12 net; no new test file);
partial update 2026-07-16 (Sprint 3.1 — Company Foundation and Caregiver Management) —
only the `accounts`/`organization_portal`/`provider_portal` rows and grand-total file/
method/class counts re-verified (+3 new test files: `test_affiliation_lifecycle.py` incl.
3 `TransactionTestCase` concurrency tests, `test_affiliation_management.py`,
`test_company_affiliation.py`);
a full re-audit of every app was not performed for any of the incremental changes.
**Last verified date:** 2026-07-14 / 2026-07-15 (partial) / 2026-07-15 (partial, Phase 2.1) /
2026-07-15 (partial, BG-022) / 2026-07-15 (partial, Sprint 2.2) / 2026-07-15 (partial,
PR #7 remediation) / 2026-07-15 (partial, Sprint 2.3) / 2026-07-15 (partial, Sprint 2.4) /
2026-07-15 (partial, PR #9 concurrency remediation) / 2026-07-15 (partial, Sprint 2.5) /
2026-07-15 (partial, Sprint 2.6) / 2026-07-15 (partial, Sprint 2.6 PR #11 KL-012 remediation) /
2026-07-16 (partial, Sprint 3.1)

---

## Grand Totals

| Metric | Count |
|--------|-------|
| Total test files | 216 (198 + 10 accumulated through Phase 1.2/1.3/2.1/BG-022/Sprint 2.2 + 1 new in the PR #9 concurrency remediation, `test_concurrency.py` + 3 new in Sprint 2.5, `test_supplier_queries.py`/`test_beneficiary_queries.py`/`test_professional_dashboard.py` + 1 new in Sprint 2.6, `test_phase2_acceptance.py`; PR #7 remediation, Sprint 2.3, and Sprint 2.4 itself added no new file; the Sprint 2.6 PR #11 KL-012 remediation expanded `test_phase2_acceptance.py`'s existing query-budget class, no new file + 3 new in Sprint 3.1, `test_affiliation_lifecycle.py`/`test_affiliation_management.py`/`test_company_affiliation.py`) |
| Total test classes | ~487 (not re-audited exactly; +3 classes in Sprint 2.4, +5 classes in the PR #9 concurrency remediation, +11 classes in Sprint 2.5, +3 classes in Sprint 2.6, +9 classes in Sprint 3.1) |
| Total test methods | 2,145 (full regression re-run 2026-07-16, Sprint 3.1 — Company Foundation and Caregiver Management) |

## Per-App Confidence

| App | Files | Methods | Auth Tests | Concurrency | Financial | Mock | **Confidence** |
|-----|-------|---------|------------|-------------|-----------|------|----------------|
| kernel | 19 | 232 | 7 | - | 5 | 2 | **STRONG** |
| accounts | 26 | 400 | 6 | 3 | - | 1 | **STRONG** |
| commission | 22 | 132 | 15 | 1 | 20 | 2 | **STRONG** |
| orders | 8 | 167 | - | - | - | - | **STRONG** |
| finance | 18 | 81 | 1 | - | 17 | 1 | **STRONG** |
| api | 14 | 97 | 7 | - | 4 | - | **HIGH** |
| public_site | 10 | 151 | 1 | - | - | - | **HIGH** |
| booking | 10 | 67 | 2 | 1 | 1 | 2 | **HIGH** |
| pricing | 6 | 69 | - | - | - | 1 | **MODERATE-HIGH** |
| portal | 9 | 74 | 1 | - | 2 | - | **MODERATE-HIGH** |
| payments | 7 | 54 | 2 | 1 | 7 | 1 | **HIGH** |
| execution | 9 | 58 | 1 | - | - | 1 | **MODERATE** |
| notifications | 4 | 53 | - | - | - | - | **MODERATE** |
| organization_portal | 6 | 60 | 2 | - | - | - | **MODERATE** |
| provider_portal | 11 | 141 | 8 | - | 3 | - | **MODERATE** |
| jobs | 1 | 35 | - | 1 | - | - | **MODERATE** |
| discovery | 5 | 42 | - | - | - | - | **MODERATE** |
| availability | 6 | 56 | - | - | - | - | **MODERATE** |
| reporting | 6 | 37 | - | - | 2 | - | **MODERATE** |
| matching | 5 | 33 | - | - | - | - | **LOW-MODERATE** |
| reviews | 6 | 39 | 1 | - | - | - | **LOW-MODERATE** |
| wallet | 5 | 34 | - | 1 | 5 | 1 | **MODERATE** |
| admin_portal | 6 | 45 | 8 | - | 1 | - | **MODERATE-HIGH** |
| common | 0 | 0 | - | - | - | - | **ZERO** |
| showcase | 0 | 0 | - | - | - | - | **ZERO** |

## Specialized Test Patterns

### Concurrency Tests (5 files)
- `booking/test_concurrency.py` — `threading.Barrier` + `select_for_update()` for concurrent assignment
- `commission/test_contract_concurrency.py` — concurrent propose/approve/reject
- `payments/test_settlement_orchestration.py` — concurrent settlement
- `wallet/test_atomicity.py` — concurrent wallet movements
- `jobs/test_jobs_foundation.py` — `select_for_update(skip_locked=True)`

### TransactionTestCase (3 files)
- `booking/test_concurrency.py`
- `commission/test_contract_concurrency.py`
- `payments/test_settlement_orchestration.py`

### Mock Usage (10 files, 5%)
Sparse mocking — test suite overwhelmingly uses real database operations.

## Key Observations

1. **Strongest coverage**: kernel (232), accounts (180), commission (132) — highest volume with cross-cutting concerns
2. **Financial testing is deep**: 72 of 196 files (37%) touch financial operations
3. **Authorization testing is broad**: 53 files across 12 apps
4. **Zero-test apps**: common (shared utilities imported everywhere) and showcase
5. **Concurrency testing is rare but strategically placed**: 5 files protect critical write paths

## Critical Test Gaps

1. `common` app has zero tests but is imported across multiple apps
2. No integration tests that exercise the full Order → Assignment → Execution → Payment → Escrow → Settlement chain end-to-end
3. No tests for the `seed_product_walkthrough` management command's reporting side effects (the source of the pre-existing flaky test)
4. Offer Marketplace Phase 1 tests are in working tree, not committed
