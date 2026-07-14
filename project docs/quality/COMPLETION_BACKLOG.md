# CURRENT GAPS AND COMPLETION BACKLOG

**Last verified HEAD:** ce3b30e0f3c06d7b058587f3e75c357bfe588415
**Last verified date:** 2026-07-14 (documentation sync + executable verification)

---

## P0 — Prevents Safe Continuation or Merge

### BG-001: Commit Phase 1 OrderOffer Implementation — **COMPLETE**

**Resolution:** OrderOffer model, migration `orders/0008_orderoffer.py`, tests,
and admin were committed in `ce3b30e` ("Repository documentation
reorganization"). Verified by `git log -- src/apps/orders/migrations/0008_orderoffer.py`
and clean working tree. Closed 2026-07-14.

### BG-002: Fix Pre-Existing Seed Test order_number Collision — **COMPLETE**

**Root cause:** Random in-run collision of the 4-digit suffix in
`orders/models.py:_generate_order_number()` (10,000 numbers/day); proven by a
1/10 isolated-run failure and two full-suite errors on 2026-07-14 at ce3b30e.
**Resolution (2026-07-14):** `Order.save()` now retries auto-generation up to
`ORDER_NUMBER_MAX_ATTEMPTS` (5) times when the database unique constraint
rejects a generated number, each attempt in its own savepoint; suffix widened
to 6 digits (10^6/day). Caller-supplied duplicates still raise immediately.
No migration required. Regression tests:
`orders/tests/test_order_number_generation.py` (8 tests incl. concurrency).
See CHANGE_LEDGER CL-017 and TEST_EXECUTION_LOG Run 009.

---

## P1 — Blocks First Complete Internal Product Workflow

### BG-003: OrderOfferService (Phase 2)

**Current evidence:** Phase 1 model exists. No service layer.
**Why needed:** Offer Marketplace cannot function without services to submit/edit/withdraw/select offers.
**Dependencies:** BG-001 (commit Phase 1)
**Affected modules:** orders
**Suggested implementation size:** Medium (1 service class + tests)
**Required tests:** Unit tests with PostgreSQL, concurrency tests
**Risk:** Medium — must not break existing assignment flow
**Not in scope:** Discovery, views, templates, APIs, payment integration

### BG-004: Implement Real PSP Adapter

**Current evidence:** Only `FakePaymentProviderAdapter` exists. All payment flows are mocked.
**Why needed:** Cannot process real payments without a real PSP.
**Affected modules:** payments
**Suggested implementation size:** Large (adapter + integration tests + configuration)
**Required tests:** Integration tests with sandbox PSP
**Risk:** High — financial correctness critical
**Not in scope:** Multiple PSP support, payment method diversity

### BG-005: Implement Real Notification Providers

**Current evidence:** Only fake SMS/email/push providers exist.
**Why needed:** Cannot send real notifications to users.
**Affected modules:** notifications
**Suggested implementation size:** Medium (per-provider adapter)
**Required tests:** Integration tests with sandbox providers
**Risk:** Medium — operational requirement
**Not in scope:** Multi-channel notification preferences

---

## P2 — Blocks External Pilot

### BG-006: Production Deployment Configuration

**Current evidence:** No docker-compose production config, no production settings beyond security headers.
**Why needed:** Cannot deploy to production.
**Affected modules:** config
**Suggested implementation size:** Medium
**Risk:** Medium
**Not in scope:** Kubernetes, auto-scaling

### BG-007: Enable Deadline Expiry Gate

**Current evidence:** `deadline_activation_enabled` defaults to DISABLED. Payment deadlines are created but don't auto-expire.
**Why needed:** Orders will remain in limbo if deadlines don't expire.
**Affected modules:** commission
**Suggested implementation size:** Small (config change + verification)
**Risk:** Medium — must verify expiry cascade works correctly
**Not in scope:** Deadline extension UI

### BG-008: Enable Pre-Service Payment Gate

**Current evidence:** `preservice_payment_enabled` defaults to DISABLED. No escrow hold before service.
**Why needed:** Financial protection for providers requires escrow.
**Affected modules:** commission, finance
**Suggested implementation size:** Medium (gate enablement + integration verification)
**Risk:** High — financial flow change
**Not in scope:** Customer payment UI

---

## P3 — Blocks Production Launch

### BG-009: Tenant Isolation Hardening

**Current evidence:** No middleware-level tenant injection. Depends on developer discipline.
**Why needed:** Cross-tenant data leak is the highest-severity security risk.
**Affected modules:** All
**Suggested implementation size:** Large (middleware + audit + row-level security)
**Risk:** High — architectural change
**Not in scope:** Multi-region deployment

### BG-010: CI Pipeline Activation

**Current evidence:** `.github/workflows/ci.yml` exists but never executed.
**Why needed:** No automated test execution on PRs.
**Affected modules:** DevOps
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Full CI/CD pipeline

### BG-011: RBAC Enforcement Audit Logging

**Current evidence:** No audit when `rbac.enforcement.enabled` is toggled.
**Why needed:** Security compliance.
**Affected modules:** kernel
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** RBAC redesign

---

## P4 — Post-Launch or Optimization

### BG-012: Remove Legacy Wallet from finance App

**Current evidence:** `finance.WalletAccount`/`WalletTransaction` superseded by `apps.wallet`.
**Why needed:** Reduce confusion.
**Affected modules:** finance
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Data migration

### BG-013: Add Tests for common App

**Current evidence:** Zero tests for shared utilities imported across apps.
**Why needed:** Regression protection for foundational code.
**Affected modules:** common
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Full coverage

### BG-014: Extract Shared Auth Guard

**Current evidence:** Each portal independently implements `_guard()`.
**Why needed:** DRY principle, single enforcement point.
**Affected modules:** All portals
**Suggested implementation size:** Medium
**Risk:** Low
**Not in scope:** Middleware redesign
