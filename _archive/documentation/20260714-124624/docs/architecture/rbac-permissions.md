# RBAC & Permission Taxonomy

Status: current as of Epic 05 (Permission-Key Registry & Authorization
Hardening). Does **not** redesign RBAC — `Role`/`RoleAssignment`/
`PermissionService`'s public evaluation contract is unchanged; Epic 05
centralized the key inventory, fixed four concrete authorization defects
(three surfaced by the centralization work itself, plus one previously
tracked defect fixed under the same Epic's explicit permission to do so
— see below), and made targeted, tested hardening changes to scope
evaluation. See `docs/adr/ADR-010_CANONICAL_PERMISSION_REGISTRY.md`
for the full decision record.

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

**Epic 05 scope-evaluation hardening** (`_scope_matches()`, targeted, not
a redesign): an unscoped (`scope=None`) check now matches only an
unscoped/platform-scoped `RoleAssignment`, not a narrower one (e.g.
`scope_type="organization"`) — previously any assignment matched an
unscoped check regardless of its own scope. A malformed `scope` dict
(missing `scope_type`/`scope_id`) and a malformed `RoleAssignment` row
(real `scope_type`, null `scope_id`) now fail closed explicitly rather
than incidentally.

## The `ownership_authorized_by` security contract

(Epic 05 Architecture Review, Major finding M1 — documentation
clarification; no behavior changed.) `ownership_authorized_by` is **not,
on its own, a standalone authorization boundary**. `PermissionService`
does not and cannot independently verify that the actor passed as
`ownership_authorized_by` actually owns or administers the resource in
question — it assumes the caller has already established that upstream,
before `require()` is ever invoked.

The normal production path is:

```
request
-> portal/service resolves the caller's own organization/resource
   (e.g. apps.organization_portal.permissions.resolve_organization())
-> that resolution IS the ownership verification
-> PermissionService.require(..., ownership_authorized_by=<verified actor>)
-> real RBAC evaluation is tried first
-> the audited ownership fallback is used only when a matching
   RoleAssignment has not yet been synced for that actor
```

If a caller ever passes the wrong actor as `ownership_authorized_by` —
for example, an admin who administers a *different* organization than
the resource being acted on — `PermissionService` will still authorize
that call once it falls back to the ownership-authorized path: the
fallback audits and allows an actor it trusts was already verified, it
does not re-derive or re-check that verification itself. **This is a
caller bug, not a `PermissionService` bug** — every caller of
`require(..., ownership_authorized_by=...)` (`AssignmentService.assign()`/
`.replace()`, `OrganizationStaffService.approve_membership()`/
`suspend_membership()`) is responsible for resolving and verifying
ownership before calling, the same way `require(actor, ...)`'s own
real-RBAC path trusts that `actor` is a genuine, already-authenticated
identity rather than re-authenticating it.

## Canonical permission-key registry

`apps.kernel.permissions` (Epic 05) is the single source of truth for
every real permission key in the platform — a lightweight, in-memory
Python registry (`PermissionRegistry`), **not** a database table and
**not** a policy engine. Populated once via `KernelConfig.ready()`
importing `apps.kernel.permissions.keys`, where every key is registered
with its `domain`/`resource`/`action`/`description` and scope hints.
Duplicate or malformed keys (not matching `<domain>.<action>` or
`<domain>.<resource>.<action>`, lowercase, dot-separated) fail at import
time — a startup failure, not a silent runtime gap.

`apps.kernel.models.rbac.Permission` — the pre-existing, migrated
"protected operations registry" model — remains dormant and unused by
design; nothing at runtime reads it (`PermissionService` evaluates
`Role.permissions`, a freeform JSON string list, exclusively). See
ADR-010 for why the Python registry, not this model, is authoritative.

Every existing per-app `permission_keys.py` module (`apps.api`,
`apps.admin_portal`, `apps.accounts`) is now a re-export facade over this
registry — same public names, same string values, zero behavior change
for any existing import. New facades exist for `apps.booking`,
`apps.finance`, `apps.execution`, replacing seven previously-hardcoded
literal permission-key strings in those apps' service modules.

A guardrail test (`apps.kernel.tests.test_permission_registry_guardrails`)
proves no production `PermissionService.require()`/`.check()` call site
uses a raw string literal, and that every facade constant resolves in the
registry.

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
Organization Isolation), corrected in Epic 05. Located in `apps.accounts`
rather than `apps.organization_portal` because enforcement happens in
service code in `apps.accounts`/`apps.booking`, not at the portal's view
layer, and `apps.accounts` is the most upstream of the two consuming apps
in the dependency graph — `apps.booking` importing from it does not
invert the graph:

| Constant | Value | Guards |
|---|---|---|
| `BOOKING_ASSIGNMENT_ASSIGN` | `booking.assignment.assign` | `AssignmentService.assign()`/`.replace()`, when called with `scope={"scope_type": "organization", ...}` — the path `OrganizationAssignmentService.assign_manual()` always uses. Re-exported from `apps.booking.permission_keys` — this is the same key every non-organization caller of `assign()` also checks, not a separate organization-specific key (see below). |
| `ORGANIZATION_MEMBERSHIP_APPROVE` | `organization.membership.approve` | `OrganizationStaffService.approve_membership()` |
| `ORGANIZATION_MEMBERSHIP_SUSPEND` | `organization.membership.suspend` | `OrganizationStaffService.suspend_membership()` |

**Epic 05 correction**: Epic 04 originally defined and granted a fourth,
separate key, `ORGANIZATION_ASSIGNMENT_ASSIGN = "organization.assignment
.assign"` — but `AssignmentService.assign()` has always checked the
literal `"booking.assignment.assign"` regardless of the `scope` kwarg;
`scope` only narrows *which* `RoleAssignment` can satisfy that one key, it
never introduced a second key. The grant never activated real RBAC for
`assign_manual()` — every call silently fell through to the
`ownership_authorized_by` audit path instead. Retired the phantom key;
`organization_admin` is now granted the canonical `BOOKING_ASSIGNMENT_ASSIGN`.
See `docs/adr/ADR-010_CANONICAL_PERMISSION_REGISTRY.md`.

Only these three keys exist because only these three enforcement points
were planned for Epic 04's approved scope — `apps.organization_portal
.permissions.resolve_organization()` already gates every
organization-portal view to an `ACTIVE`, `ADMIN`-role
`OrganizationMembership`, so no other `OrgMembershipRole` value
(`OPERATOR`, `CAREGIVER`, `ACCOUNTANT`, `SUPPORT`, `MANAGER`) has an
enforcement point to hold a permission for yet — a key was deliberately
not added for `organization.order.view_eligible`/`organization.staff
.view`/`organization.reports.view`/`organization.capacity.view` for
exactly this reason (see `apps.accounts.permission_keys`'s own module
docstring).

The `organization_admin` `Role` (seeded by `apps/accounts/management
/commands/seed_auth_roles.py`, also lazily created by
`apps.accounts.services.organization_rbac.OrganizationRoleSyncService` if
missing) is the only role carrying these three keys.

**Architecture Review remediation (Epic 04, PR #28 required remediation
item 2): none of these three keys is actually consulted by a
`PermissionService.require()`/`.check()` call anywhere in this Epic's
code, as merged.** `AssignmentService.assign()` checks the literal string
`"booking.assignment.assign"`, not `ORGANIZATION_ASSIGNMENT_ASSIGN` — the
two are different strings and never match. `approve_membership()` and
`suspend_membership()` contain no `PermissionService` call of any kind.
Every action these three keys were intended to gate is, today, authorized
entirely through `PermissionService.require()`'s pre-existing
`ownership_authorized_by` fallback — a real, already-verified,
correctly tenant/organization-scoped actor, never an open bypass, never
mislabeled as system context — not through a real `RoleAssignment` check
against one of these keys. This is a deliberate, tracked, temporary
limitation of Epic 04, not a security gap. Wiring these three call sites
to check their intended key is Permission-Key Registry & Authorization
Hardening (Epic 05) scope, not Epic 04's — see that Epic's own
documentation once merged. See `apps.accounts.permission_keys`'s own
per-constant docstrings for the identical statement kept next to each key.

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

## Epic 04: organization-scoped RoleAssignment rows now have a writer (evaluation still not wired to a real call site)

`RoleAssignment.scope_type="organization"`/`scope_id` and
`PermissionService._scope_matches()` existed and were correctly evaluated
since Module 08, but had zero production writers until Epic 04 (Enterprise
Organization Isolation). `apps.accounts.services.organization_rbac
.OrganizationRoleSyncService` is now the sole writer — see
`docs/adr/ADR-009_ORGANIZATION_ELIGIBILITY_AND_SCOPED_RBAC.md` for the
full design.

## Epic 05: canonical registry, four authorization defects, scope hardening

See `docs/adr/ADR-010_CANONICAL_PERMISSION_REGISTRY.md` for the full
decision record. In summary:

- The unscoped-check-matches-any-assignment gap Epic 04 identified and
  deliberately deferred is now fixed (see "The evaluator" above).
- Three concrete authorization defects, surfaced by migrating every real
  enforcement call site to a canonical constant, are fixed with dedicated
  tests: the phantom `organization.assignment.assign` key (see the
  `apps/accounts/permission_keys.py` table above), `OrganizationStaffService
  .approve_membership()`/`suspend_membership()` having zero enforcement
  despite granted keys, and `AssignmentService.replace()` having zero
  authorization of any kind.
- A fourth authorization defect is also fixed here — not surfaced by the
  centralization work itself, but a previously tracked defect
  (`technical-debt-register.md`, "`ReviewSubmissionService` reviewer-vs-
  order-customer ownership gap") that this Epic's scope explicitly
  permitted fixing: `ReviewSubmissionService.submit_review()` never
  verified `reviewer_person_id` was actually the order's own customer —
  any authenticated user in the tenant holding the `reviews.submit`
  permission could submit a review for *any* completed order, not just
  their own. Fixed with a service-layer check (`order.customer_profile
  .person_id != reviewer_person_id` denies), enforced before `Review`
  persistence, with dedicated allow/deny tests
  (`apps.reviews.tests.test_reviewer_ownership_authorization`).
- The role-catalog divergence noted below is now centralized (not
  resolved — the two catalogs remain intentionally distinct) in
  `apps.kernel.role_catalog`, with a `reconcile_role_permissions`
  management command for operational drift correction.

## Role-seeding catalogs

`apps.kernel.role_catalog` (Epic 05) is now the single module both
role-seeding commands import their role definitions from:
`apps.kernel.management.commands.seed_tenant` (`DEV_BOOTSTRAP_ROLES`,
hyphenated slugs, seeds a `dev`-slug bootstrap tenant) and
`apps.accounts.management.commands.seed_auth_roles`
(`DEFAULT_TENANT_ROLES`, underscored slugs, seeds the real default
`salmandyar` tenant, `apps.kernel.services.tenant_service.TenantService`'s
own default). These remain two genuinely distinct role sets, not one
merged/renamed taxonomy — see ADR-010 for why forcing a merge would be a
destructive database rename out of Epic 05's scope. The one clear-cut
divergence (`"platform-owner"` vs `"platform_owner"`, almost certainly the
same real-world role) is recorded in `apps.kernel.role_catalog
.KNOWN_SLUG_ALIASES` as a known, deliberate, not-yet-resolved alias.
