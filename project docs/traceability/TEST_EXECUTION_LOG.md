# TEST EXECUTION LOG

**Repository:** taasisatSenior
**Session:** Offer Marketplace Analysis and Contract Development

---

## Run 001 — Full Django Test Suite

```
Command: python manage.py test --verbosity=2
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Environment variables: DATABASE_ENGINE=django.db.backends.postgresql, GIS_ENABLED=false
Working directory: C:\Users\hp\Desktop\MIMO\1\taasisatSenior\src
Date/time: 2026-07-13
```

| Metric | Value |
|--------|-------|
| Total tests found | 1632 |
| Passed | 1632 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Duration | 320.613 seconds |
| Result | OK |

**Relevant output:**
```
Found 1632 test(s).
Creating test database for alias 'default' ('test_marketplace')...
... (1632 tests) ...
Ran 1632 tests in 320.613s
OK
Destroying test database for alias 'default'...
```

**Environmental deviations:** None. PostgreSQL 16 running locally on port 5432. GIS_ENABLED=false (no PostGIS).

---

## Run 002 — E2E Validation Script (Attempt 1-6, Failures)

```
Command: python e2e_validation.py
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (marketplace, persistent)
Working directory: C:\Users\hp\Desktop\MIMO\1\taasisatSenior\src
Date/time: 2026-07-13
```

| Metric | Value |
|--------|-------|
| Total steps | 18 |
| Passed (final run) | 18 |
| Failed (script development) | 6 attempts with parameter errors |

**Note:** This is a standalone validation script, not part of the official Django test suite. Failures were in script inputs (wrong function signatures, missing permissions), not in production code.

---

## Run 003 — Django System Check

```
Command: python manage.py check
Result: System check identified no issues (0 silenced)
```

---

## Run 004 — Migration Check

```
Command: python manage.py makemigrations --check --dry-run
Result: Cosmetic drift detected (accounts: 7 Alter field changes, kernel: 50+ Alter field/index changes)
Nature: Django version-skew artifact. manage.py migrate reports "no migrations to apply" for these.
```

---

## Run 005 — Database Migration (Fresh)

```
Command: python manage.py migrate
Result: 55 migrations applied successfully
Range: contenttypes.0001_initial through wallet.0001_initial
```

---

## Future Test Executions

Append future test runs below this line.

---

## Run 006 — Phase 1 Remediation: manage.py check

```
Command: python manage.py check
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f (unchanged)
Settings module: config.settings.testing
Database: PostgreSQL 16
Date/time: 2026-07-14
Exit code: 0
```

| Metric | Value |
|--------|-------|
| Result | System check identified no issues (0 silenced) |

---

## Run 007 — Phase 1 Remediation: makemigrations --check

```
Command: python manage.py makemigrations --check --dry-run
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16
Date/time: 2026-07-14
Exit code: 1 (expected — cosmetic accounts/kernel drift)
```

| Metric | Value |
|--------|-------|
| Accounts drift | 7 Alter field changes (cosmetic metadata) |
| Kernel drift | 50+ Alter field/index changes (cosmetic metadata) |
| Orders migration proposed | **None** |
| Nature | Django version-skew artifact. No real schema changes. |

---

## Run 008 — Phase 1 Remediation: OrderOffer Targeted Tests

```
Command: python manage.py test apps.orders.tests.test_order_offer_model --verbosity=2
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
Exit code: 0
```

| Metric | Value |
|--------|-------|
| Total tests found | 40 |
| Passed | 40 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Duration | 1.494 seconds |
| Result | OK |

---

## Run 009 — Phase 1 Remediation: Full Orders Tests

```
Command: python manage.py test apps.orders.tests --verbosity=1
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
Exit code: 0
```

| Metric | Value |
|--------|-------|
| Total tests found | 119 |
| Passed | 119 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Duration | 9.037 seconds |
| Result | OK |

---

## Run 010 — Phase 1 Remediation: Full Regression Suite

```
Command: python manage.py test --verbosity=1
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
Exit code: 1
```

| Metric | Value |
|--------|-------|
| Total tests found | 1672 |
| Passed | 1671 |
| Failed | 0 |
| Errors | 1 |
| Skipped | 0 |
| Duration | 351.569 seconds |
| Result | FAILED (1 error) |

**Error details:**
```
ERROR: test_reporting_does_not_change_service_supplier_count
  (apps.kernel.tests.test_seed_product_walkthrough.SeedProductWalkthroughReportSideEffectTest)
Cause: IntegrityError — duplicate order_number (ORD-20260713-7329)
Location: seed_product_walkthrough.py line 928 → create_operator_order
Nature: Pre-existing race condition in seed command. order_number auto-generation
         uses random 4-digit suffix that can collide within same second.
         NOT related to OrderOffer model or Phase 1 changes.
```

---

## Run 008 — Current-HEAD Verification (Documentation Sync Task)

```
Commit SHA: ce3b30e0f3c06d7b058587f3e75c357bfe588415 (main)
Branch during verification: claude/taasisat-senior-state-verify-9dzzlm
  (= ce3b30e + documentation-only commit ed33e47, IMPLEMENTATION_ROADMAP.md;
   no src/ differences vs ce3b30e)
Git status before verification: working tree clean
Settings module: config.settings.testing
Environment: cloud verification container
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13 (Ubuntu 24.04)
Database: PostgreSQL (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift (accounts ×8 field alters, kernel manager/index-rename/field alters) — same behavior recorded in CL-013 at previous HEAD |
| `python manage.py migrate` | 0 | All migrations apply cleanly, including orders.0008_orderoffer |
| Seed test isolated ×10 (`SeedProductWalkthroughReportSideEffectTest.test_reporting_does_not_change_service_supplier_count`) | 9×0, 1×1 | Run 10 failed IN ISOLATION: IntegrityError duplicate order_number `ORD-20260714-1003` |
| `python manage.py test --verbosity=1` (full suite) | 1 | Ran 1662, FAILED (errors=2). Both errors: duplicate order_number in seed walkthrough (`SeedProductWalkthroughDatasetTest.setUpClass` — its 10 tests therefore not run, explaining 1662 vs 1672 — and `SeedProductWalkthroughReportSideEffectTest`) |

**Failure analysis:** Both failures are the known seed order_number collision:
`orders/models.py:_generate_order_number()` uses a 4-digit random suffix; the
seed walkthrough creates enough same-day orders that in-run collisions occur
randomly (birthday problem). The 1/10 isolated-run failure proves this is a
RANDOM IN-RUN COLLISION, not an inter-test race or order-dependent effect.
`git show ce3b30e` confirms neither `_generate_order_number()` nor the seed
command was modified by ce3b30e (last seed change: 697d7ea) — PRE-EXISTING.

**Classification of HEAD ce3b30e:**
`GREEN_EXCEPT_CONFIRMED_PRE_EXISTING_FLAKY_TEST` — all 1660 executed
non-seed-affected tests passed; the only failures trace to the pre-existing
random collision (BG-002).
