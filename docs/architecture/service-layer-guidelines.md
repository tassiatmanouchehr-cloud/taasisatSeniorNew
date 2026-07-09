# Service Layer Guidelines

Status: descriptive — this documents the convention every module from
Module 08 onward has actually followed, and flags the few older modules
that predate it. Not a new rule; a written-down existing one.

## The pattern

Every app with mutating operations puts them in a `services/` package,
never in `models.py` or a view:

```
apps/<app>/
  models.py                  # data shape + append-only/immutability guards only
  services/
    __init__.py               # re-exports the public surface
    errors.py                  # class XError(Exception) — the module's exception type
    configuration.py           # class XConfiguration — ConfigResolver wrapper (if the module has tunables)
    <capability>_service.py    # classmethod-only service classes
```

### `errors.py`

One exception class per module (`WalletError`, `PaymentError`,
`PricingError`, `ReviewError`, `DiscoveryError`, `AvailabilityError`,
`FinanceError`, `ReportingError`). No shared base class across modules —
each is an independent `Exception` subclass with a safe, human-written
message (never used for stack traces or internal detail). This is why
`apps/api/exception_handler.py` maps them by an explicit allowlist rather
than a common base type — see `api-guidelines.md`.

Three modules predate this convention and keep their exception classes
inline in the relevant service file instead of a dedicated `errors.py`:
`booking.AssignmentError`, `execution.ExecutionError`,
`orders.OrderValidationError`/`OrderStateError`. Functionally identical,
just organized differently. Not worth moving for its own sake.

### `configuration.py`

A thin wrapper over `apps.kernel.services.config_resolver.ConfigResolver`.
Service code must never call `ConfigResolver` directly — always through
the module's own `XConfiguration` class, so all of a module's tunable
keys and defaults live in one place. Present in 9 modules today
(availability, booking, discovery, finance, matching, payments, pricing,
reporting, wallet) plus kernel's own `RBACConfiguration`. Modules without
one (accounts, orders, execution, notifications, reviews, api) simply
have no tunable values yet — add one only when a real config key is
needed, not preemptively.

### DTOs

Read-only cross-module data returns a **frozen dataclass**, never an ORM
object, when the data crosses a context boundary for reporting/display
purposes (`apps.reporting.dto.*`, `apps.discovery.services.dto
.SearchResultItem`, `apps.matching.services.eligibility.EligibilityResult`,
`apps.kernel.events.base.DomainEvent`, `apps.payments.services.dto
.PaymentResult`). There is no DRF wiring inside domain services — DTOs
are framework-agnostic; `apps/api/serializers/` is what converts them for
transport.

## Tenant scoping

Two valid patterns, both correct:

1. **`TenantScopedManager.for_tenant(tenant_id)`** — the default for most
   models (`Order`, `SupplierAssignment`, `ExecutionSession`, `Wallet`,
   `PaymentIntent`, `Review`, `Quote`, `FinancialDocument`, …).
2. **Explicit `.filter(tenant_id=tenant_id)`** — required for the handful
   of models that don't have `TenantScopedManager` (see
   `technical-debt-register.md` for the full list — `ServiceSupplier`,
   `Person`, `UserAccount`, `Role`, `RoleAssignment`,
   `ReputationSnapshot`, `WalletBalanceSnapshot`, `OrganizationProfile`,
   `SettlementItem`, `PromotionCondition`/`PromotionEffect`). Every
   current call site does this correctly — it's just easier to forget
   than pattern 1, since nothing enforces it structurally.

**Rule for new code**: if a model lacks `TenantScopedManager`, every query
against it must include an explicit `tenant_id=` (or a relation that's
already tenant-scoped, e.g. `.filter(wallet=wallet)` where `wallet` was
itself already tenant-checked). Never trust a bare `.objects.get(id=...)`
on one of these models to be tenant-safe.

## Mutation discipline

- All balance/state-changing operations wrapped in `@transaction.atomic`.
- Append-only ledger models (`WalletTransaction`, `PaymentCallback`,
  `PaymentTransaction`) override `save()`/`delete()` to raise after
  creation — the pattern originates in Module 05
  (`finance.PaymentTransaction`) and is now standard for anything meant
  to be an immutable audit trail.
- Idempotency: `credit()`/`debit()`/etc. on `WalletTransactionService` and
  `PaymentIntentService.create_intent()`/`PaymentCallbackService
  .process_callback()` all accept/derive an idempotency key and check for
  an existing row before creating a new one, with an `IntegrityError`
  fallback for the race window.

## What a service must never do

- Return an HTTP response, a `Serializer`, or anything DRF-shaped.
- Accept `request` as a parameter. (`apps/api/permissions.py` takes
  `request` because it's API-layer plumbing, not a domain service.)
- Import `apps.api`.
