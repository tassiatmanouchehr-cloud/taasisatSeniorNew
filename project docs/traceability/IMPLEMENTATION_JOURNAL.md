# IMPLEMENTATION JOURNAL

**Repository:** taasisatSenior
**Session:** Offer Marketplace Phase 1 — Domain Foundation

---

## Initial Phase 1 Implementation

**Date:** July 13, 2026
**Status:** COMPLETE

Created OrderOffer model, migration 0008, admin registration, 24 tests.
Initial migration had conditional UniqueConstraint (active-only per supplier).
Had premature PaymentIntent reference in docstring.
Had temporary cleanup tooling (cleanup_test_db.py).

---

## Architecture Review Findings

**Date:** July 13, 2026
**Status:** ADDRESSED

Identified 5 issues:
1. Premature PaymentIntent reference in model docstring
2. Active-only uniqueness policy (should be canonical)
3. Temporary cleanup tooling (cleanup_test_db.py)
4. Missing domain properties
5. Documentation inconsistencies

---

## First Remediation Attempt

**Date:** July 13, 2026
**Status:** SUPERSEDED

Applied 5 remediations but introduced two problems:
1. Created two migrations (0008 + 0009) instead of squashing into one
2. Had complex loop test that failed due to order_number collision

---

## Completion Remediation

**Date:** July 14, 2026
**Status:** COMPLETE

### Changes Applied
1. Squashed 0008+0009 into single 0008 with canonical constraint
2. Added can_edit, can_withdraw, can_select domain properties
3. Replaced complex loop test with 7 individual status tests
4. Verified admin (supplier__display_name valid)
5. Removed temporary cleanup tooling

---

## Final Verified Phase 1 State

**Date:** July 14, 2026
**Status:** VERIFIED

### Migration
- Single migration: `orders/0008_orderoffer.py`
- Dependencies: kernel.0011, orders.0007, AUTH_USER_MODEL
- No 0009 migration exists
- No phantom kernel migration exists

### Database Constraints
- Unconditional UniqueConstraint: `(order, supplier)` — one canonical offer per supplier per order
- Conditional UniqueConstraint: `(order)` WHERE status='selected' — one selected offer per order

### Domain Properties
- `can_edit` → True only when status == SUBMITTED
- `can_withdraw` → True only when status == SUBMITTED
- `can_select` → True only when status == SUBMITTED
- All 7 status values tested for all 3 properties

### Test Results (with real exit codes)

| Command | Exit Code | Discovered | Passed | Failed | Errors | Duration |
|---------|-----------|-----------|--------|--------|--------|----------|
| manage.py check | 0 | — | — | 0 | 0 | — |
| makemigrations --check | 1 | — | — | — | — | — |
| OrderOffer targeted | 0 | 40 | 40 | 0 | 0 | 1.494s |
| Full Orders | 0 | 119 | 119 | 0 | 0 | 9.037s |
| Full regression | 1 | 1672 | 1671 | 0 | 1 | 351.569s |

**Note:** The full regression error (exit code 1) is in `test_seed_product_walkthrough.py` — a pre-existing order_number collision race condition, NOT related to OrderOffer or Phase 1 changes.

### Files Implemented

| File | Purpose | Lines |
|------|---------|-------|
| `src/apps/orders/models.py` | OrderOfferStatus, OFFER_TERMINAL_STATUSES, OrderOffer | +115 |
| `src/apps/orders/admin.py` | OrderOfferAdmin | +8 |
| `src/apps/orders/migrations/0008_orderoffer.py` | Database migration | 52 |
| `src/apps/orders/tests/test_order_offer_model.py` | 40 unit tests | 481 |

### Files Deleted
- `src/apps/orders/migrations/0009_orderoffer_canonical.py` (squashed into 0008)
- `src/cleanup_test_db.py` (temporary tooling)
- `src/apps/kernel/migrations/0012_orderoffer*.py` (phantom migrations)

### Architecture Decision
ADM-013: One canonical OrderOffer per (order, supplier). Unconditional uniqueness for stable identity, audit history, and reporting.

### Phase 1 Merge Recommendation
**Approved.** All remediations complete. All tests pass (except 1 pre-existing seed error). Single migration. No phantom files. No Phase 2 contamination.

---

## Permanent Repository Memory

**Date:** July 14, 2026
**Status:** CREATED

Created `PROJECT_CONTINUATION.md` and `NEXT_TASK.md` at repository root to ensure any future AI assistant (with zero conversation memory) can continue the project correctly.

**Why introduced:** The project has accumulated significant analysis, architecture decisions, and implementation across multiple sessions. Without persistent repository-level documentation, a new AI session would need to re-discover everything from scratch. These files provide the minimum viable context for continuation.

**Files created:**
- `PROJECT_CONTINUATION.md` — permanent project memory (status, decisions, blockers, governance)
- `NEXT_TASK.md` — next task definition (investigate seed test, then Phase 2)

**Scope:** Documentation only. No code changes.

---

## BG-002 — Order Number Collision Fix

**Date:** 2026-07-14
**Status:** COMPLETE

### Root Cause

`orders/models.py:_generate_order_number()` produced `ORD-YYYYMMDD-` plus a
4-digit random suffix — only 10,000 possible numbers per day against a
globally unique `order_number` column. The seed walkthrough creates enough
same-day orders that in-run birthday-problem collisions occur randomly.
Verified at ce3b30e: 1/10 isolated runs failed; full suite hit the collision
in two test classes (`SeedProductWalkthroughDatasetTest.setUpClass` and
`SeedProductWalkthroughReportSideEffectTest`).

### Chosen Fix (Option D — retry + stronger entropy)

1. `Order.save()` retries auto-generation up to `ORDER_NUMBER_MAX_ATTEMPTS`
   (5) times when the database rejects a generated number with the
   `order_number` unique violation. Each attempt runs inside
   `transaction.atomic()` (a savepoint inside caller transactions), so a
   rejected insert does not poison `@transaction.atomic` order-creation
   services. Any other IntegrityError, and any caller-supplied duplicate
   `order_number`, still raises immediately.
2. Suffix widened from 4 to 6 digits (10^6 numbers/day). Format family
   unchanged: `ORD-YYYYMMDD-NNNNNN`, 19 chars, well within max_length=30.
   Existing 4-digit rows remain valid; no consumer parses the suffix and no
   test asserted the old width (verified by repository-wide grep).

### Alternatives Rejected

- **A. Retry only:** fixes the flake but leaves a 10k/day global ceiling —
  retries would degrade sharply as daily volume grows.
- **B. Stronger entropy only:** reduces but does not eliminate collision
  failures; the defect class survives.
- **C. Database sequence:** deterministic, but changes the public format to
  monotonic (information leak: daily order volume), requires new DB state,
  and is more than the minimal fix.
- **Timestamp component:** rejected per task constraint — concurrent calls
  in the same instant still collide.

### Concurrency Safety

The unique constraint remains the sole arbiter — generation never
check-then-inserts. Under concurrent creation, the second inserter receives
the unique violation from PostgreSQL and retries with a fresh number.
Proven by `OrderNumberConcurrencyTest` (TransactionTestCase, 2 threads,
barrier, forced identical first draw), mirroring
`apps.booking.tests.test_concurrency`.

### Files Changed

| File | Change |
|------|--------|
| `src/apps/orders/models.py` | 6-digit suffix; `ORDER_NUMBER_SUFFIX_LENGTH`, `ORDER_NUMBER_MAX_ATTEMPTS`, `_is_order_number_collision()`; bounded retry in `Order.save()` |
| `src/apps/orders/tests/test_order_number_generation.py` | NEW — 8 regression tests (format, forced collision retry, no overwrite, bounded retry, explicit-duplicate passthrough, savepoint behavior, concurrency) |

### Migration Impact

None. No field or constraint changed; `makemigrations --check` output is
identical to the pre-fix state (pre-existing cosmetic accounts/kernel drift
only, zero orders entries).

### Rollback Method

`git revert` of the fix commit (or `git checkout` of the two files). No data
cleanup needed — 6-digit numbers are ordinary values under the existing
constraint.
