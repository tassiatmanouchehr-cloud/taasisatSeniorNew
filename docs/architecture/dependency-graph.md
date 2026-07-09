# App Dependency Graph

Status: current as of Module 18. Derived by grepping every `from apps.X`
import across the codebase (production code, not tests) on 2026-07-09.
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
                                    └── reporting (→ everything above, read-only)
                                          └── api (→ everything, read + thin write)
```

A **lower-numbered app never imports a higher-numbered one.** `api` is the
apex: nothing imports `apps.api` except `config/urls.py`'s routing
`include()` — verified by grep, zero matches elsewhere.

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

## Verified clean

- Nothing imports `apps.api` except `config/urls.py`.
- No app writes to `apps.kernel.models.event_outbox.EventOutbox` directly
  except `apps.kernel.services.event_publisher.EventPublisher`.
- No app outside `apps.wallet` defines a model named `Wallet` or
  `WalletTransaction` except `apps.finance.models.wallet` (explicitly
  frozen/legacy — see `wallet-finance-boundary.md`).
