# DUPLICATE IMPLEMENTATIONS

---

## DG-001: Wallet Implementations

**Business concept:** Digital wallet for party balance management

| | Implementation A | Implementation B |
|---|---|---|
| **Location** | `apps/finance/models/wallet.py` | `apps/wallet/models.py` |
| **Models** | WalletAccount, WalletTransaction | Wallet, WalletTransaction, WalletBalanceSnapshot |
| **Service** | `apps/finance/services/wallet_service.py` | `apps/wallet/services/wallet_service.py` + `wallet_transaction_service.py` |
| **Idempotency** | No | Yes (unique constraint) |
| **Balance snapshots** | No | Yes |
| **Transaction types** | Basic | 6 types (CREDIT, DEBIT, REFUND, etc.) |

**Current callers:** `SettlementOrchestrationService` calls `apps.wallet` (canonical)
**Runtime source of truth:** `apps.wallet`
**Risk:** MEDIUM — new developers may use wrong app
**Recommendation:** Mark `apps/finance` wallet as DEPRECATED in code comments.

---

## DG-002: Configuration Services (Acceptable Pattern)

**Business concept:** Runtime configuration resolution

6+ configuration services across apps, all wrapping `kernel.ConfigResolver`. Each defines its own keys and defaults.

**Risk:** LOW — all delegate to same ConfigResolver
**Recommendation:** Acceptable. Could extract base class but not urgent.

---

## DG-003: Query Services (Naming Variation)

**Business concept:** Read-only data access

Each app has its own QueryService with varying names: QueryService, Queries, *QueryService.

**Risk:** LOW — each app owns its reads
**Recommendation:** Acceptable. Naming could be standardized.

---

## DG-004: Presentation Services (No Duplication)

Each portal has its own presentation services. No overlap — each serves a different portal.

**Risk:** NONE
**Recommendation:** No action needed.

---

## DG-005: Authorization Guards (Per-Portal)

Each portal independently implements `_guard()` / `require_admin_permission()` / `require_permission()`.

**Risk:** MEDIUM — each portal independently implements auth guard
**Recommendation:** Consider extracting a shared auth middleware or base view mixin.
