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

`apps/accounts/permission_keys.py`, introduced in Epic 04 (Enterprise
Organization Isolation). Located in `apps.accounts` rather than
`apps.organization_portal` because enforcement happens in service code in
`apps.accounts`/`apps.booking`, not at the portal's view layer, and
`apps.accounts` is the most upstream of the two consuming apps in the
dependency graph — `apps.booking` importing from it does not invert the
graph:

| Constant | Value | Guards |
|---|---|---|
| `ORGANIZATION_ASSIGNMENT_ASSIGN` | `organization.assignment.assign` | `AssignmentService.assign()`, when called with `scope={"scope_type": "organization", ...}` — the path `OrganizationAssignmentService.assign_manual()` always uses |
| `ORGANIZATION_MEMBERSHIP_APPROVE` | `organization.membership.approve` | `OrganizationStaffService.approve_membership()` |
| `ORGANIZATION_MEMBERSHIP_SUSPEND` | `organization.membership.suspend` | `OrganizationStaffService.suspend_membership()` |

Only these three keys exist because only these three enforcement points
exist in Epic 04's approved scope — `apps.organization_portal.permissions
.resolve_organization()` already gates every organization-portal view to
an `ACTIVE`, `ADMIN`-role `OrganizationMembership`, so no other
`OrgMembershipRole` value (`OPERATOR`, `CAREGIVER`, `ACCOUNTANT`,
`SUPPORT`, `MANAGER`) has an enforcement point to hold a permission for
yet — a key was deliberately not added for `organization.order
.view_eligible`/`organization.staff.view`/`organization.reports.view`/
`organization.capacity.view` for exactly this reason (see
`apps.accounts.permission_keys`'s own module docstring).

The `organization_admin` `Role` (seeded by `apps/accounts/management
/commands/seed_auth_roles.py`, also lazily created by
`apps.accounts.services.organization_rbac.OrganizationRoleSyncService` if
missing) is the only role carrying these three keys.

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

## Epic 04: organization-scoped RoleAssignment activation

`RoleAssignment.scope_type="organization"`/`scope_id` and
`PermissionService._scope_matches()` existed and were correctly evaluated
since Module 08, but had zero production writers until Epic 04 (Enterprise
Organization Isolation). `apps.accounts.services.organization_rbac
.OrganizationRoleSyncService` is now the sole writer — see
`docs/adr/ADR-009_ORGANIZATION_ELIGIBILITY_AND_SCOPED_RBAC.md` for the
full design. One important, unchanged pre-existing behavior this
activation makes newly relevant: `_scope_matches()` returns `True`
immediately when the caller's `check()`/`require()` call passes no `scope`
kwarg at all (`scope is None`), regardless of the assignment's own
`scope_type` — an organization-scoped `RoleAssignment` therefore also
satisfies any *unscoped* check for the same `permission_key`. Not
exploitable today (every organization-isolation call site always passes
an explicit `scope`), but a real gap for a future Permission-Key Registry
& Authorization Hardening Epic to close, not something Epic 04 changed
(see its own explicit "Do not replace the RBAC model" constraint).

Two independent, unreconciled role-seeding catalogs exist in this
codebase — `apps.kernel.management.commands.seed_tenant`'s hyphenated
`DEFAULT_ROLES` (seeded against a `dev`-slug tenant) and
`apps.accounts.management.commands.seed_auth_roles`'s underscored `ROLES`
(seeded against the real default `salmandyar` tenant,
`apps.kernel.services.tenant_service.TenantService`'s own default). Epic
04 extends only the latter — see `technical-debt-register.md` for the
tracked divergence.
