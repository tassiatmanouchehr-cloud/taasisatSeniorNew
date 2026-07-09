# RBAC & Permission Taxonomy

Status: current as of Module 18. This sprint documents the existing
taxonomy and fixes one small inconsistency (a stray literal string). It
does **not** redesign RBAC — see `technical-debt-register.md` for what a
future RBAC hardening module might address.

## The evaluator

`apps.kernel.services.permission_service.PermissionService` (Module 08) is
the sole evaluator of `Role`/`RoleAssignment` for an authorization
decision. `check(actor, permission_key, *, tenant_id, scope=None) -> bool`
is pure; `require(...)` enforces it and raises
`apps.kernel.services.errors.PermissionDenied` on failure, auditing every
denial. Fail-closed: no tenant, no actor, no matching active
`RoleAssignment`, or a role that doesn't carry the key all deny.
`RBACConfiguration.get_enforcement_enabled(tenant_id)` (default `True`)
can disable enforcement per-tenant — used for internal/system call sites
that predate a real actor being available.

`actor` may be a `kernel.UserAccount` or a `kernel.Person` instance.

## There is no permission registry table

`Role.permissions` is a **freeform JSON string list** — any string can be
granted to a role, and `PermissionService` never validates a `permission_key`
against a canonical list. Nothing stops a typo from silently creating a
permission nobody can ever be granted correctly. This has been true since
Module 08 and remains true after this sprint (documenting, not fixing —
see the constraint against RBAC redesign).

## The only taxonomy that exists today

`apps/api/permission_keys.py`, introduced in Module 17B, when the first
real API endpoints needed RBAC checks:

| Constant | Value | Guards |
|---|---|---|
| `REPORTING_READ` | `reporting.read` | `GET /api/v1/sample/order-counts/`, `GET /api/v1/sample/providers/` |
| `DISCOVERY_SUPPLIERS_READ` | `discovery.suppliers.read` | `GET /api/v1/discovery/suppliers/` |
| `PRICING_QUOTES_CREATE` | `pricing.quotes.create` | `POST /api/v1/pricing/quotes/` |
| `REVIEWS_SUBMIT` | `reviews.submit` | `POST /api/v1/reviews/` |
| `REVIEWS_READ` | `reviews.read` | `GET /api/v1/suppliers/{id}/reputation/` |
| `WALLET_READ` | `wallet.read` | `GET /api/v1/wallet/balance/`, `GET /api/v1/wallet/transactions/` |
| `PAYMENTS_INTENTS_CREATE` | `payments.intents.create` | `POST /api/v1/payments/intents/` |
| `PAYMENTS_ATTEMPTS_CREATE` | `payments.attempts.create` | `POST /api/v1/payments/intents/{id}/attempts/` |

`POST /api/v1/payments/callbacks/fake/` intentionally requires no
permission key — see `wallet-finance-boundary.md` and the view's own
docstring for why (it simulates an unauthenticated PSP webhook).

## Naming convention

`<domain>.<resource>.<action>` or `<domain>.<action>` when there's a
single obvious resource (`reviews.submit`, `wallet.read`). Lowercase,
dot-separated, no versioning in the key itself (the key names a
capability, not an endpoint — multiple endpoints may share one key, as
`reporting.read` already does).

## Module 18 fix

`apps/api/views/reporting.py` (written in Module 17A, before
`permission_keys.py` existed) still used the literal string
`"reporting.read"` instead of the constant introduced a module later.
Fixed in this sprint — same string value, so **zero behavior change**;
purely a consistency fix so every view in `apps/api/views/` now imports
its permission key from `permission_keys.py` rather than hardcoding it.

## Default roles have no permissions populated

`apps/kernel/management/commands/seed_tenant.py`'s `DEFAULT_ROLES` (14
roles: platform-owner, organization-owner, customer, support-user,
finance-user, etc.) are seeded with `name`/`slug`/`description` only —
`permissions` defaults to `[]`. Nothing in this codebase currently
assigns the keys above to any of the seeded default roles. A deployment
wanting the Module 17B API endpoints actually usable by, say, the
`customer` role must grant those keys explicitly (via
`RoleAssignment`/`Role.permissions`, or the test helper
`apps.kernel.tests.rbac_helpers.grant_permissions`). This is a real gap
for anyone standing up a working deployment today — flagged in
`technical-debt-register.md`, not fixed here (deciding which roles get
which keys is a product/security decision, not an architecture-hygiene
one).
