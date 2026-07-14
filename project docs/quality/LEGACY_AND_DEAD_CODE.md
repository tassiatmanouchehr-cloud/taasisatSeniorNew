# LEGACY AND DEAD CODE CANDIDATES

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

---

## Dead Code Candidates

### DC-001: Legacy Wallet (finance.WalletAccount, finance.WalletTransaction)

**Path:** `apps/finance/models/wallet.py`
**Classification:** LEGACY_CANDIDATE
**Evidence:** `apps.wallet` is the canonical wallet with full service layer, idempotency, and balance snapshots. `SettlementOrchestrationService` calls `apps.wallet`, not `apps.finance` wallet.
**Known callers:** `apps/finance/services/wallet_service.py` exists but is not called by the production settlement path.
**Deletion risk:** LOW — other code may reference these models for historical reasons.
**Confidence:** HIGH

### DC-002: Legacy Escrow Methods

**Path:** `apps/finance/services/escrow_service.py:52-129`
**Classification:** LEGACY_CANDIDATE
**Evidence:** `hold()`, `release()`, `refund()` methods at lines 52-129 are documented as "dead code, zero real callers." The production path uses the PR-B methods (lines 131-633).
**Deletion risk:** LOW — documentation says they exist for reference.
**Confidence:** HIGH

### DC-003: Demo Job Handlers

**Path:** `apps/jobs/handlers/demo.py`
**Classification:** DORMANT
**Evidence:** `demo.no_op`, `demo.always_fail`, `demo.echo` — test-only handlers, not used in production.
**Deletion risk:** LOW — used in job system tests.
**Confidence:** HIGH

### DC-004: Fix/Setup Scripts

**Path:** `src/fix_perms.py`, `src/setup_db.py`, `src/e2e_validation.py`
**Classification:** DORMANT
**Evidence:** Temporary scripts created during initial analysis. Not part of the application.
**Deletion risk:** LOW — may be useful for development setup.
**Confidence:** HIGH

### DC-005: UI Showcase App

**Path:** `apps/showcase/`
**Classification:** DORMANT
**Evidence:** Static UI component demos at `/ui/`. No business logic, no models, no tests. May not be needed in production.
**Deletion risk:** LOW — could be useful for design review.
**Confidence:** MEDIUM

---

## Dormant Feature Flags

The system has extensive feature gating via `ConfigurationKey`/`ConfigurationValue` and `FeatureFlag` models. Most gates default to DISABLED:

| Gate | Default | Purpose |
|------|---------|---------|
| `deadline_activation_enabled` | DISABLED | Payment deadline auto-expiry |
| `preservice_payment_enabled` | DISABLED | Escrow hold before service |
| `escrow_production_enabled` | DISABLED | Production escrow path |
| `objection_automation_enabled` | DISABLED | Auto-approve objection periods |
| `dispute_release_enabled` | DISABLED | Dispute flow |
| `availability_enforcement_enabled` | DISABLED | Availability checking |
| `auto_accept_enabled` | DISABLED | Auto-accept assignments |

These are intentional gates for incremental rollout, not dead code.

---

## Migration Candidates

| Migration | Status | Note |
|-----------|--------|------|
| orders.0008_orderoffer.py | IN WORKING TREE | Phase 1, not committed |
| kernel.0012_orderoffer*.py | DELETED | Phantom migration, removed |
| orders.0009_orderoffer_canonical.py | DELETED | Squashed into 0008 |

No abandoned migrations found in committed code.
