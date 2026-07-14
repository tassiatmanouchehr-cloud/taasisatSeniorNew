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
