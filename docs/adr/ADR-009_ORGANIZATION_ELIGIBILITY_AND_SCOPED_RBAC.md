# ADR-009 — Order-Organization Eligibility as an Explicit Junction, Organization RBAC via Existing Scope Machinery

## Status

Accepted — Epic 04 (Enterprise Organization Isolation), Sprints 1-3.

## Context

`GAP_ANALYSIS.md` documented a real, production-readiness-blocking gap:
the organization portal's Assignment Center
(`apps.orders.services.queries.OrderQueryService.list_unassigned_for_tenant()`)
was tenant-wide, not organization-scoped. Any organization admin in a
tenant could see and assign staff to any unclaimed order, including one a
competing organization had some claim to. `Order` had no
organization-eligibility concept of any kind to filter on.

Separately, `apps.kernel.models.rbac.RoleAssignment.scope_type`/`scope_id`
and `PermissionService._scope_matches()` already fully implemented
organization-scoped authorization evaluation (verified: `_scope_matches()`
correctly compares `scope_type`/`scope_id`) — but zero production code
ever wrote a `RoleAssignment(scope_type="organization", ...)` row. Every
organization-admin action was authorized via an `ownership_authorized_by`
fallback in `PermissionService.require()`, not real RBAC.

Three alternatives were evaluated for the eligibility gap: a direct
`organization` FK on `Order` (cannot represent zero or multiple eligible
organizations without a breaking migration later); a formal
offer/routing/bidding model (this is the "open bidding" / "invitation-
based routing" feature explicitly out of scope for this Epic — building it
now to solve an isolation problem would be disproportionate); and tenant-
wide visibility with policy-filtered queries computed at read time (no
audit trail of who granted eligibility or when, cannot express
"withdrawn" cleanly).

For the eligibility *policy* itself, a "single organization in a tenant is
automatically eligible" default was considered and explicitly rejected by
the System Architect: it is a count-based implicit rule, and — decisively
— direct inspection of `apps.orders.services.order_creation
.create_public_order()`/`create_operator_order()` found **no existing
business signal of any kind** (no organization FK, no category-to-
organization mapping, no operator-to-organization mapping) that could
legitimately identify an eligible organization at order-creation time.
There was no deterministic signal to build an automatic policy from.

## Decision

**`OrderOrganizationEligibility`** — a new junction model
(`apps.orders.models`) between `Order` and `accounts.OrganizationProfile`,
written exclusively through `apps.orders.services.eligibility_service
.OrderEligibilityService` (enforced by a guardrail test,
`apps.kernel.tests.test_architecture_guardrails
.OrderOrganizationEligibilitySoleWriterTest`). One row per `(order,
organization)` pair, `status` ACTIVE/WITHDRAWN, no automatic writer
anywhere — every row is the result of an explicit `grant()` call (a
platform/tenant operator action via the `grant_order_eligibility`
management command in this Epic; no in-app UI is built, per the "no broad
organization-portal UI redesign" non-goal). An organization additionally
retains the ability to act on an order it has already been assigned,
independent of eligibility state (the "post-assignment ownership" rule,
`OrganizationAssignmentService._already_assigned_to_organization()`) — an
organization never loses the ability to act on work it already owns
merely because its eligibility grant was later withdrawn.

`OrganizationRoleSyncService`
(`apps.accounts.services.organization_rbac`) activates the pre-existing
scope machinery: it is the sole writer of organization-scoped
`RoleAssignment` rows, called from the two places an `ADMIN`-role
`OrganizationMembership` transitions status
(`affiliations.approve_affiliation_request()`,
`OrganizationStaffService.approve_membership()`/`suspend_membership()`).
Only `OrgMembershipRole.ADMIN` is synced — `apps.organization_portal
.permissions.resolve_organization()` already gates every organization-
portal view to an active admin membership, so no other role_type has an
enforcement point to hold a permission for in this Epic. A new partial
`UniqueConstraint` on `RoleAssignment` (`(tenant, user, role, scope_type,
scope_id)`, condition `is_active=True`) makes the sync idempotent and
concurrency-safe. The pre-existing `ownership_authorized_by` fallback in
`AssignmentService.assign()` is deliberately left in place, not removed —
it is what guarantees no organization admin is ever locked out during the
window between deployment and the backfill command completing.

`apps.accounts.services.supplier_bridge.get_or_create_supplier_for_caregiver()`
now creates a `SupplierType.ORGANIZATION_PROVIDER`-typed supplier (an
enum value that existed since Module 03 but was production-unreachable)
for a caregiver whose `provider_type` is `ORGANIZATION_AFFILIATED`. The
financial policy is unchanged and explicit:
`FinancialPartyService.resolve_party_for_supplier()` still keys strictly
on `supplier_type == SupplierType.ORGANIZATION`, so an affiliated
caregiver's earnings continue to settle to their own
`FinancialParty`/wallet, never the organization's.

## Consequences

- **Architecture Review remediation (PR #28 required remediation item
  2)**: "activates the pre-existing scope machinery" above describes the
  *writer* side only — `OrganizationRoleSyncService` correctly creates and
  maintains organization-scoped `RoleAssignment` rows. It does not, by
  itself, mean any of the three organization permission keys these rows
  carry (`ORGANIZATION_ASSIGNMENT_ASSIGN`, `ORGANIZATION_MEMBERSHIP
  _APPROVE`, `ORGANIZATION_MEMBERSHIP_SUSPEND`) is actually checked by a
  `PermissionService.require()`/`.check()` call anywhere in this Epic —
  none is. `AssignmentService.assign()` checks the literal
  `"booking.assignment.assign"`, a different string;
  `approve_membership()`/`suspend_membership()` have no permission check
  at all. Every action these keys were meant to gate remains authorized
  through the pre-existing `ownership_authorized_by` fallback in this
  Epic — safe (the fallback is itself correctly scoped), but not the
  keyed RBAC check this ADR's title describes. See
  `docs/architecture/rbac-permissions.md`'s "The three organization
  permission keys" section for the full accounting. Wiring these three
  call sites to their intended key is Permission-Key Registry &
  Authorization Hardening (Epic 05) scope.
- Existing single-organization tenants see a real, deliberate behavior
  change: an order has zero eligible organizations by default and is
  invisible to the Assignment Center until an operator explicitly grants
  it. This is the intended fix, not a side effect.
- A caregiver affiliated before this Epic keeps an `INDEPENDENT_PROVIDER`-
  typed `ServiceSupplier` until `reconcile_organization_provider_suppliers`
  is run (a one-time, idempotent reconciliation — `SupplierRegistry
  .get_or_create_supplier()`'s `defaults` only apply on first creation).
- Two independent, unreconciled role-seeding catalogs remain in the
  codebase (`apps.kernel.management.commands.seed_tenant`'s hyphenated
  `DEFAULT_ROLES` against a `dev` tenant, `apps.accounts.management
  .commands.seed_auth_roles`'s underscored `ROLES` against the real
  default `salmandyar` tenant) — this Epic extends only the latter (the
  one the real runtime tenant uses) and does not reconcile the two; see
  `technical-debt-register.md`.
- `PermissionService._scope_matches()`'s existing behavior — an unscoped
  `check()`/`require()` call (no `scope` kwarg) matches ANY assignment
  regardless of the assignment's own `scope_type` — is unchanged. Not
  exploitable by anything in this Epic (every organization-isolation
  enforcement point always passes an explicit `scope`), but it is exactly
  the gap a later Permission-Key Registry & Authorization Hardening Epic
  is expected to close.
