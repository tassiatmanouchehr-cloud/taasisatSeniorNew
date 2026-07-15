# TEST CONFIDENCE MATRIX

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f (per-app table below);
partial update 2026-07-15 (phase1-registration-manual-verification) — only the
`accounts`/`admin_portal` rows and grand-total method count were re-verified;
partial update 2026-07-15 (phase2-caregiver-professional-profile-foundation) — only
`accounts`/`provider_portal`/`public_site` rows and grand-total method count re-verified;
a full re-audit of every app was not performed for either incremental change.
**Last verified date:** 2026-07-14 / 2026-07-15 (partial) / 2026-07-15 (partial, Phase 2.1)

---

## Grand Totals

| Metric | Count |
|--------|-------|
| Total test files | 204 (198 + 6 accumulated through Phase 1.2/1.3/2.1) |
| Total test classes | ~440 (not re-audited exactly) |
| Total test methods | 1,874 (full regression re-run 2026-07-15, phase2-caregiver-professional-profile-foundation) |

## Per-App Confidence

| App | Files | Methods | Auth Tests | Concurrency | Financial | Mock | **Confidence** |
|-----|-------|---------|------------|-------------|-----------|------|----------------|
| kernel | 19 | 232 | 7 | - | 5 | 2 | **STRONG** |
| accounts | 24 | 317 | 6 | 2 | - | 1 | **STRONG** |
| commission | 22 | 132 | 15 | 1 | 20 | 2 | **STRONG** |
| orders | 7 | 159 | - | - | - | - | **STRONG** |
| finance | 17 | 75 | 1 | - | 17 | 1 | **STRONG** |
| api | 14 | 97 | 7 | - | 4 | - | **HIGH** |
| public_site | 7 | 93 | 1 | - | - | - | **HIGH** |
| booking | 10 | 67 | 2 | 1 | 1 | 2 | **HIGH** |
| pricing | 6 | 69 | - | - | - | 1 | **MODERATE-HIGH** |
| portal | 9 | 74 | 1 | - | 2 | - | **MODERATE-HIGH** |
| payments | 7 | 54 | 2 | 1 | 7 | 1 | **HIGH** |
| execution | 9 | 58 | 1 | - | - | 1 | **MODERATE** |
| notifications | 4 | 53 | - | - | - | - | **MODERATE** |
| organization_portal | 5 | 49 | 2 | - | - | - | **MODERATE** |
| provider_portal | 8 | 68 | 4 | - | 2 | - | **MODERATE** |
| jobs | 1 | 35 | - | 1 | - | - | **MODERATE** |
| discovery | 5 | 42 | - | - | - | - | **MODERATE** |
| availability | 6 | 37 | - | - | - | - | **MODERATE** |
| reporting | 6 | 37 | - | - | 2 | - | **MODERATE** |
| matching | 5 | 33 | - | - | - | - | **LOW-MODERATE** |
| reviews | 6 | 33 | 1 | - | - | - | **LOW-MODERATE** |
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
