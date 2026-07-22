# DUPLICATION AND SOURCE OF TRUTH REGISTER

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

---

## Duplicate Group 1: Wallet Implementations

**Business concept:** Digital wallet for party balance management

**Implementation A:** `apps/finance/models/wallet.py` — `WalletAccount`, `WalletTransaction`
- Uses `finance.FinancialParty` as owner
- `WalletAccount.balance` cached field
- `WalletTransaction` with source_document, payment_transaction FKs

**Implementation B:** `apps/wallet/models.py` — `Wallet`, `WalletTransaction`, `WalletBalanceSnapshot`
- Also uses `finance.FinancialParty` as owner
- `Wallet.balance` cached field
- `WalletTransaction` with idempotency_key unique constraint
- `WalletBalanceSnapshot` for audit trail
- Full service layer: `WalletService`, `WalletTransactionService`

**Current callers:**
- `SettlementOrchestrationService` calls `apps.wallet` (canonical)
- `finance.WalletService` exists but callers are legacy

**Runtime source of truth:** `apps.wallet`
**Tests:** `apps/wallet` (34 methods), `apps/finance` (tests reference legacy wallet)
**Differences:** `apps.wallet` has idempotency, balance snapshots, 6 transaction types. `apps.finance` wallet is simpler.
**Risk of divergence:** MEDIUM — both exist in codebase, new developers may use wrong one
**Confidence:** HIGH
**Recommended future decision:** Deprecate `finance.WalletAccount`/`WalletTransaction`. Mark as legacy. Update ADR-004.

---

## Duplicate Group 2: Configuration Services

**Business concept:** Runtime configuration resolution

**Implementations:**
- `apps/commission/services/configuration_service.py` — CommissionConfiguration
- `apps/availability/services/configuration_service.py` — AvailabilityConfiguration
- `apps/matching/services/configuration_service.py` — MatchingConfiguration
- `apps/booking/services/configuration.py` — BookingConfiguration
- `apps/pricing/services/configuration_service.py` — PricingConfiguration
- `apps/payments/services/configuration_service.py` — PaymentConfiguration
- `apps/kernel/services/config_resolver.py` — ConfigResolver (generic)

**Pattern:** Each app has its own `ConfigurationService` that wraps `ConfigResolver.get()` with typed defaults.

**Runtime source of truth:** `kernel.ConfigurationKey` + `kernel.ConfigurationValue` tables, resolved by `ConfigResolver`
**Differences:** Each app defines its own keys and defaults. No duplication of data, only of the wrapper pattern.
**Risk of divergence:** LOW — all delegate to the same ConfigResolver
**Confidence:** HIGH
**Recommended future decision:** Acceptable pattern. Could extract a base class but not urgent.

---

## Duplicate Group 3: Query Services

**Business concept:** Read-only data access

**Implementations:**
- `apps/orders/services/queries.py` — OrderQueryService, CatalogQueryService
- `apps/booking/services/queries.py` — QueryService
- `apps/execution/services/queries.py` — QueryService
- `apps/commission/services/financial_core_queries.py` — FinancialCoreQueryService
- `apps/notifications/services/queries.py` — NotificationQueryService
- `apps/availability/services/query_service.py` — QueryService

**Pattern:** Each app has a QueryService for read operations. Name varies (QueryService, Queries, *QueryService).
**Risk of divergence:** LOW — each app owns its own reads
**Confidence:** HIGH
**Recommended future decision:** Acceptable. Naming could be standardized.

---

## Duplicate Group 4: Presentation Services

**Business concept:** Transform domain models into view-ready data

**Implementations:**
- `apps/portal/services/dashboard_service.py` etc.
- `apps/provider_portal/services/profile_service.py`
- `apps/organization_portal/services/profile_service.py`
- `apps/public_site/services/` (4 services)

**Pattern:** Each portal has presentation services. No duplication — each serves a different portal.
**Confidence:** HIGH
**Recommended future decision:** No action needed.

---

## Duplicate Group 5: Authorization Logic

**Business concept:** Permission checking

**Implementations:**
- `apps/kernel/services/permission_service.py` — canonical PermissionService
- `apps/portal/views.py:_guard()` — customer auth
- `apps/provider_portal/views.py:_guard()` — provider auth
- `apps/organization_portal/views.py:_guard()` — org auth
- `apps/admin_portal/views.py:require_admin_permission()` — admin auth
- `apps/api/permissions.py:require_permission()` — API auth

**Pattern:** Each portal has its own auth guard function that wraps `require_authenticated()` + tenant resolution + role-specific checks. The service-level `PermissionService.require()` is the canonical enforcement point.

**Risk of divergence:** MEDIUM — each portal independently implements its guard
**Confidence:** HIGH
**Recommended future decision:** Consider extracting a shared auth middleware or base view mixin.
