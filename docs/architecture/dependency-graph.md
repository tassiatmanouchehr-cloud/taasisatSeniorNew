# App Dependency Graph

Status: current as of Module 18, plus the `apps.portal` addition below
(Customer Experience Phase 1 remediation — this diagram never mentioned
`apps.portal` or `apps.admin_portal` at all before this update; only
`portal`'s own new imports are added here, verified by the same
regenerate command used everywhere else in this doc). Derived by
grepping every `from apps.X` import across the codebase (production
code, not tests) on 2026-07-09.
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
                              └── wallet, payments (→ finance, wallet)
                                    └── notifications (read by portal below;
                                        also reached by kernel.events.handlers,
                                        see the one deliberate exception below)
                                    └── reporting (→ everything above, read-only)
                                          └── api (→ everything, read + thin write)
                                          └── portal (→ accounts, orders, finance,
                                              notifications, pricing, wallet — read
                                              + thin write, server-rendered UI)
```

A **lower-numbered app never imports a higher-numbered one.** `api` is the
apex: nothing imports `apps.api` except `config/urls.py`'s routing
`include()` — verified by grep, zero matches elsewhere. `apps.portal` sits
alongside `api`/`reporting` at the same wide-read end of the graph — see
below — but nothing imports `apps.portal` either, so it doesn't change
anything upstream of it.

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

## Verified clean

- Nothing imports `apps.api` except `config/urls.py`.
- No app writes to `apps.kernel.models.event_outbox.EventOutbox` directly
  except `apps.kernel.services.event_publisher.EventPublisher`.
- No app outside `apps.wallet` defines a model named `Wallet` or
  `WalletTransaction` except `apps.finance.models.wallet` (explicitly
  frozen/legacy — see `wallet-finance-boundary.md`).
