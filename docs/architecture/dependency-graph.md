# App Dependency Graph

Status: current as of PR #24's merge (Epic 02 — Marketplace Operational
Experience, `main` @ `bb95a902df4874076542884edaad81c4a6e9073d`), plus
the `apps.provider_portal`/`apps.organization_portal` additions below (the
`apps.portal` section was added in the Customer Experience Phase 1
remediation and remains unchanged), plus the `apps.payments -> apps.orders`
and `apps.payments -> apps.jobs` edges added below (Epic 03 Sprint 1 —
Financial Settlement, PR pending). Derived by grepping every
`from apps.X` import across the codebase (production code, not tests) on
2026-07-10.
Re-derive with:

```bash
for app in kernel accounts orders matching booking execution finance \
           notifications availability pricing discovery reviews wallet \
           payments reporting api; do
  echo "=== $app ==="
  grep -rhoE "from apps\.[a-z_]+" apps/$app --include="*.py" \
    | grep -v __pycache__ | sort -u | grep -v "from apps\.$app$"
done
```

## Layering rule

Dependencies flow **one way**, roughly in module-number order:

```
kernel
  └── accounts
        └── orders
              └── matching, booking (→ matching), execution (→ booking),
                  availability, pricing, discovery, reviews
                        └── finance (→ execution, booking, orders)
                              └── wallet, payments (→ finance, wallet, orders, jobs)
                                    └── notifications (read by portal below;
                                        also reached by kernel.events.handlers,
                                        see the one deliberate exception below)
                                    └── reporting (→ everything above, read-only)
                                          └── api (→ everything, read + thin write)
                                          └── portal (→ accounts, orders, finance,
                                              notifications, pricing, wallet — read
                                              + thin write, server-rendered UI)
                                          └── provider_portal (→ accounts, availability,
                                              booking, execution, finance, notifications,
                                              orders, reporting, reviews, wallet — read
                                              + thin write, server-rendered UI)
                                          └── organization_portal (→ accounts,
                                              availability, booking, notifications,
                                              orders, reporting — read + thin write,
                                              server-rendered UI)
```

A **lower-numbered app never imports a higher-numbered one.** `api` is the
apex: nothing imports `apps.api` except `config/urls.py`'s routing
`include()` — verified by grep, zero matches elsewhere. `apps.portal`,
`apps.provider_portal`, and `apps.organization_portal` sit alongside
`api`/`reporting` at the same wide-read end of the graph — see below — but
nothing imports any of the three portals either, so none of them change
anything upstream.

Notably, `apps.provider_portal` is the first app in this graph to import
both `apps.booking` and `apps.execution` directly (`apps.execution`
already depends on `apps.booking`, so this doesn't create a cycle) — it
does so specifically to orchestrate "confirm assignment, then create the
execution session" as two sequential calls at the view layer, since
`apps.booking` itself cannot import `apps.execution` (see *the one
deliberate exception*-style note in `apps.provider_portal.views.
assignment_confirm_view`'s docstring).

## `apps.payments` import shape (Epic 03 Sprint 1)

`apps.payments` gained two new import edges, both verified by grepping
`apps/payments` for `from apps\.`:

- **`apps.orders`** (previously it depended only on `apps.finance`/
  `apps.wallet`, per ADR-005). `SettlementOrchestrationService`
  (`apps/payments/services/settlement_orchestration_service.py`) imports
  `apps.orders.models.Order` to resolve the `Order` a
  `PaymentIntent.reference_id` names before settling. This does not
  invert the graph: `orders` already sits upstream of `finance`, which
  already sits upstream of `payments`, so `payments` importing `orders`
  directly is a shortcut through an already-established one-way
  dependency, not a new direction.
- **`apps.jobs`** (Architecture Review remediation, Critical Finding 1 —
  settlement failure recovery). `apps/payments/jobs.py` imports
  `apps.jobs.registry.JobRegistry` (to register a
  `payments.settlement.retry` handler from `PaymentsConfig.ready()`) and
  `apps.payments/services/payment_callback_service.py` imports
  `apps.jobs.services.job_service.JobService` (to durably, idempotently
  enqueue a retry when synchronous settlement fails). `apps.jobs` owns no
  models outside its own `JobDefinition`/`JobRun` and imports no business
  app itself (`apps.jobs.registry`'s own docstring: "deliberately
  dependency-free... must never import from any business app") — it is a
  dependency-free infrastructure module, safely importable from any
  business app without inversion risk, the same role `apps.kernel` plays
  at the root of this graph. `apps.payments` is the first business app to
  actually enqueue/register against it (previously only
  `apps.jobs.handlers`' own demo handlers were registered).

`PaymentCallbackService.process_callback()` triggers
`SettlementOrchestrationService` after its own atomic block commits, on a
first-time `SUCCEEDED` acceptance only — never on an idempotent replay or
a rejection. See `apps.payments.services.settlement_orchestration_service`
and `apps.payments.jobs`'s own module docstrings for the full money-flow
and recovery sequence.

## The one deliberate exception

`apps.kernel.events.handlers` imports `apps.notifications.models`
(`Notification`, `NotificationChannel`, `NotificationStatus`). This looks
backwards (`kernel` is the foundation) but is intentionally guarded:

- The handler module is never imported at `apps.kernel` package load time
  (see `apps/kernel/events/__init__.py`) — it's only imported and
  registered from `apps.notifications.apps.NotificationsConfig.ready()`.
- This means `kernel` has no *load-time* dependency on `notifications`;
  the coupling only exists once `notifications` chooses to wire itself in.
- Documented in the handler module's own docstring since Module 09.

This is the only cross-app import inside `apps.kernel` production code
that reaches into a business app. It is intentional, not drift.

## Read-only aggregation apps (`discovery`, `reporting`) — a different shape

Both apps own no models. `discovery` reads `kernel.ServiceSupplier` +
`reviews.ReputationSnapshot`; `reporting` reads across orders/booking/
execution/finance/wallet/reviews. Their imports are wide by design — they
exist specifically to aggregate across bounded contexts for read purposes.
This is not layering drift; it's the intended shape of a read model.

## `apps.api` import shape

Every view module imports the relevant domain app's `services` package
(never a service's *internals*) plus, in three places, a handful of
models for simple tenant-scoped `.get()` lookups:

| View file | Model imports | Why |
|---|---|---|
| `views/pricing.py` | `ServiceCategory`, `ServiceSupplier`, `Order` | Resolve request-body IDs into tenant-scoped objects before calling `QuoteService.generate_quote()` |
| `views/reviews.py` | `Order`, `ServiceSupplier` | Same — resolve `order_id`/`supplier_id` before calling the review services |
| `views/payments.py` | `PaymentIntent`, `PaymentAttempt`, `PaymentProvider` | Tenant-scoped lookup before `start_attempt()`; provider-reference lookup for the fake callback |

No other model imports exist in `apps/api/views/`. See `api-guidelines.md`
for the rule this satisfies, and
`apps/kernel/tests/test_architecture_guardrails.py` for the automated
check that enforces it (Module 18).

## `apps.portal` import shape

Customer Experience Phase 1. Verified by grepping `apps/portal` for
`from apps\.` (production code, not tests): `apps.accounts`,
`apps.finance`, `apps.notifications`, `apps.orders`, `apps.pricing`,
`apps.wallet`. Unlike `apps.api`, `apps/portal/views.py` imports **zero**
models — every read and write goes through a `services` package call:

| Domain | Service(s) called from `apps/portal/views.py` |
|---|---|
| `apps.accounts` | `CareRecipientService` (create/update/list/ownership-scoped `get_for_customer`) |
| `apps.orders` | `OrderQueryService`, `CatalogQueryService`, `OrderTimelineService`, `OrderShareLinkService`, `create_public_order()` |
| `apps.notifications` | `NotificationQueryService` |
| `apps.finance` | `FinancialPartyService.resolve_party_for_customer()` |
| `apps.wallet` | `WalletService.get_wallet_or_none()` |
| `apps.pricing` | `QuoteService.generate_quote()` |

`OrderQueryService`, `CatalogQueryService`, `OrderTimelineService`
(`apps/orders/services/`) and `NotificationQueryService`
(`apps/notifications/services/`) were added specifically so `apps.portal`
would have a service to call instead of touching the ORM directly — an
earlier review of this module found `apps/portal/views.py` calling
`.objects.filter()`/`.count()`/`get_object_or_404(queryset, ...)` directly
in nine view functions, the same anti-pattern `ApiViewOrmDisciplineTest`/
`AdminPortalOrmDisciplineTest` exist to prevent elsewhere. `apps/portal/views.py`
is now held to the same zero-ORM standard as `apps/admin_portal/views.py`
by `PortalOrmDisciplineTest` (`apps/kernel/tests/test_architecture_guardrails.py`).

`apps.notifications` itself was never given a position in the layering
diagram above until this update (a pre-existing gap, not introduced by
this addition) — it sits after `wallet`/`payments` in build order but is
a low-coupling app (owns its own models, reached elsewhere only via the
guarded `kernel.events.handlers` exception above); `apps.portal` reading
from it does not change that.

## `apps.provider_portal` import shape

Epic 02 (Provider Experience Phase 1). Verified by grepping
`apps/provider_portal` for `from apps\.` (production code, not tests):
`apps.accounts`, `apps.availability`, `apps.booking`, `apps.execution`,
`apps.finance`, `apps.notifications`, `apps.orders`, `apps.reporting`,
`apps.reviews`, `apps.wallet`. Like `apps.portal`, `apps/provider_portal/
views.py` imports **zero** models directly — every read/write goes
through a `services` package call:

| Domain | Service(s) called from `apps/provider_portal/views.py` |
|---|---|
| `apps.accounts` | `resolve_supplier_for_user()` — the *only* place this app touches a concrete profile model, and only via this one resolver, never `CaregiverProfile` directly |
| `apps.booking` | `ProviderAssignmentQueryService`, `ProviderAssignmentActionService` |
| `apps.execution` | `ProviderExecutionQueryService`, `ProviderExecutionService`, plus `ExecutionService.create_session()` (called directly, once, immediately after a successful `confirm` — the cross-boundary orchestration point described above) |
| `apps.availability` | `AvailabilityQueryService`, `WorkingWindowService`, `BlockedPeriodService`, `CapacityService` |
| `apps.reporting` | `ProviderReportService` |
| `apps.reviews` | `ReputationService` |
| `apps.finance` | `FinancialPartyService.resolve_party_for_customer()`-equivalent for suppliers |
| `apps.notifications` | `NotificationQueryService` |

## `apps.organization_portal` import shape

Epic 02 (Organization Experience Phase 1). Verified by grepping
`apps/organization_portal` for `from apps\.` (production code, not
tests): `apps.accounts`, `apps.availability`, `apps.booking`,
`apps.notifications`, `apps.orders`, `apps.reporting`. Same zero-ORM
discipline as the other two portals:

| Domain | Service(s) called from `apps/organization_portal/views.py` |
|---|---|
| `apps.accounts` | `list_administered_organizations()`/`resolve_organization()`, `OrganizationStaffService`, `resolve_supplier_for_user()` |
| `apps.booking` | `OrganizationAssignmentService.assign_manual()` |
| `apps.orders` | `OrderQueryService` (`list_unassigned_for_tenant`, `list_recent_unassigned_for_tenant`, `count_unassigned_for_tenant`) |
| `apps.availability` | `CapacityService` |
| `apps.reporting` | `ProviderReportService.list_reports_for_suppliers()` |
| `apps.notifications` | `NotificationQueryService` |

Both new portals are held to the same `*OrmDisciplineTest` standard as
`apps.portal`/`apps.api`/`apps.admin_portal` —
`ProviderPortalOrmDisciplineTest` and `OrganizationPortalOrmDisciplineTest`
in `apps/kernel/tests/test_architecture_guardrails.py`.

## Verified clean

- Nothing imports `apps.api` except `config/urls.py`.
- No app writes to `apps.kernel.models.event_outbox.EventOutbox` directly
  except `apps.kernel.services.event_publisher.EventPublisher`.
- No app outside `apps.wallet` defines a model named `Wallet` or
  `WalletTransaction` except `apps.finance.models.wallet` (explicitly
  frozen/legacy — see `wallet-finance-boundary.md`).
