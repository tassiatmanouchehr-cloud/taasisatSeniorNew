# ADR-010 — Canonical Permission-Key Registry Authority, and the Defects It Surfaced

## Status

Accepted — Epic 05 (Permission-Key Registry & Authorization Hardening).

## Context

Before this Epic, permission-key strings were scattered as literals across
service modules (`apps.finance`, `apps.booking`, `apps.execution`) or
lived in three independent, uncoordinated per-app `permission_keys.py`
modules (`apps.api`, `apps.admin_portal`, `apps.accounts`, the last added
in Epic 04). No validation existed anywhere: nothing prevented a duplicate
key, a malformed key, a role being granted a key nothing ever checks, or a
service checking a key nothing ever grants.

The repository also already contains `apps.kernel.models.rbac.Permission`
— a "protected operations registry" model, migrated, with a unique `key`
field, `module_id`/`resource_type`/`action`/`description`/`default_roles`
metadata. Direct inspection (grep across the entire codebase, production
code only) confirmed **zero** production writers of this model — nothing
at runtime ever reads `Permission.objects` either; `PermissionService`
evaluates `Role.permissions` (a freeform JSON string list) exclusively.

## Decision — registry authority (System Architect's recommended default, confirmed)

**A lightweight, in-memory Python registry (`apps.kernel.permissions`) is
authoritative.** `apps.kernel.models.rbac.Permission` remains unchanged
and dormant. Populating it would require synchronizing two parallel
sources of truth (Python constants and database rows) for a model with no
runtime consumer today — pure ongoing cost, zero benefit, and exactly the
dual-authority problem the System Architect's guidance warned against.
Nothing about this decision forecloses populating `Permission` later as a
read-only *projection* of the Python registry, if a genuine operational
need for a queryable/database-backed inventory emerges (e.g. an
admin-portal permission browser) — that would still keep the Python
registry as the single source of truth, `Permission` rows generated from
it, never hand-maintained.

`apps.kernel.permissions.registry.PermissionRegistry` is a plain
in-memory dict, populated once via `KernelConfig.ready()` importing
`apps.kernel.permissions.keys` (every `register()` call at that module's
scope). It validates key format (`<domain>.<action>` or
`<domain>.<resource>.<action>`, lowercase, dot-separated — the existing,
already-documented convention) and rejects duplicates at import time —
a malformed or duplicate key fails Django startup, not a runtime request.

Existing per-app `permission_keys.py` modules (`apps.api`,
`apps.admin_portal`, `apps.accounts`) become re-export facades over this
registry — same public names, same string values, zero behavior change
for any existing caller. New facades were added for `apps.booking`,
`apps.finance`, `apps.execution`, replacing seven previously-hardcoded
literal permission-key strings.

## Defects fixed in this Epic

Migrating every real `PermissionService.require()`/`.check()` call site
to a canonical constant required tracing, for the first time, exactly
which string each call site actually checks against exactly which string
each role grant actually contains. This surfaced three real,
independent authorization defects, each fixed with dedicated tests (see
commit history on this Epic's branch):

1. **Epic 04 granted a phantom key.** `apps.accounts.permission_keys
   .ORGANIZATION_ASSIGNMENT_ASSIGN = "organization.assignment.assign"`
   was granted to the `organization_admin` role and asserted (by Epic 04's
   own tests, in isolation) to work — but `AssignmentService.assign()`
   checks the literal `"booking.assignment.assign"` regardless of the
   `scope` kwarg passed to it. `scope` narrows *which* RoleAssignment can
   satisfy the one real key; it was never a second key. The grant never
   activated real RBAC for `assign_manual()` — every call silently kept
   falling through to the `ownership_authorized_by` audit trail. Retired
   the phantom key; corrected the grant to the canonical
   `BOOKING_ASSIGNMENT_ASSIGN`.

2. **Two granted keys had no enforcement at all.**
   `OrganizationStaffService.approve_membership()`/`suspend_membership()`
   had `"organization.membership.approve"`/`"organization.membership
   .suspend"` defined and granted, but neither method ever called
   `PermissionService.require()`. Fixed by adding the check to both,
   mirroring `AssignmentService.assign()`'s exact `ownership_authorized_by`
   fallback shape (no lockout, same guarantee as everywhere else this
   pattern is used).

3. **`AssignmentService.replace()` had zero authorization of any kind.**
   `assign()` has always required a permission; `replace()` (a
   reassignment — the same underlying capability) required nothing. No
   production caller exists yet (confirmed by inspection); closed before
   one is ever wired up rather than after.

None of these three would have been found by code review of any single
file in isolation — each required cross-referencing what a role *grants*
against what a service actually *checks*, which the registry migration is
what forced.

A fourth authorization defect is also fixed in this Epic, sourced
differently from the three above — not surfaced by the centralization
work itself, but a previously tracked defect this Epic's approved scope
explicitly permitted fixing:

4. **Reviewer ownership validation.** *Previous behavior*:
   `ReviewSubmissionService.submit_review()` verified an order was
   `COMPLETED`, had an assigned supplier, and wasn't already reviewed for
   that supplier — but never verified `reviewer_person_id` was actually
   the order's own `customer_profile.person_id`. *Architectural risk*:
   any authenticated user in the tenant holding the `reviews.submit`
   permission could submit a review attributed to themselves for *any*
   completed order, not just their own — a reputation-integrity gap.
   *Remediation*: an explicit ownership check
   (`order.customer_profile_id is None or order.customer_profile
   .person_id != reviewer_person_id` raises `ReviewError`), placed before
   both the duplicate-review check and `Review` persistence, with
   dedicated allow/deny tests (`apps.reviews.tests
   .test_reviewer_ownership_authorization`). *Why it belongs in Epic 05*:
   this defect predates Epic 05 — it was identified and documented
   (`technical-debt-register.md`, "`ReviewSubmissionService`
   reviewer-vs-order-customer ownership gap") during an earlier module and
   deliberately left unfixed at the time because that module's scope was
   API plumbing, not domain-service authorization changes. Epic 05's own
   approved scope explicitly named this defect and authorized fixing it
   here if the fix was small, well-specified, and dependency-safe — it
   is: a single service-layer check, no new model, no new permission key,
   no change to any other caller.

## Related, narrower decision — scope evaluation hardening

While reasoning about the phantom-key defect, a second, independent gap
was found in `PermissionService._scope_matches()`: an **unscoped**
`check()`/`require()` call (`scope=None`, the shape every platform-wide
caller uses) matched **any** `RoleAssignment` regardless of that
assignment's own `scope_type` — meaning an organization-scoped grant also
silently satisfied a platform-wide check. Not exploitable by anything that
existed before this Epic (every organization-scoped grant is new in Epic
04, and every organization-isolation call site already passes an explicit
`scope`), but fixed here rather than left for a future caller to
inadvertently depend on. Also hardened: explicit fail-closed handling for
a malformed `scope` dict (missing keys) and a malformed `RoleAssignment`
row (real `scope_type`, null `scope_id`) — both previously failed only
incidentally, via string comparisons that happened to not match.
`RoleAssignment`/`Role`/`PermissionService`'s public evaluation contract
(`check()`/`require()`) is otherwise completely unchanged — this is not a
RBAC redesign.

## Related, narrower decision — role catalog reconciliation

Two independent, uncoordinated role-seeding commands existed:
`apps.kernel.management.commands.seed_tenant` (hyphenated slugs, seeds a
`dev`-slug bootstrap tenant) and `apps.accounts.management.commands
.seed_auth_roles` (underscored slugs, seeds the real default `salmandyar`
tenant). These are not the same taxonomy with cosmetic differences — they
cover genuinely distinct, only partially-overlapping role sets. Merging
them into one renamed taxonomy would mean renaming live `Role`/
`RoleAssignment` database rows, a destructive operation out of this
Epic's scope without a dedicated, separate migration. `apps.kernel
.role_catalog` is the reconciliation this Epic does make: both commands'
role definitions now live in one shared module, permission keys validated
against the canonical registry, and the one clear-cut divergence
(`"platform-owner"` vs `"platform_owner"`, almost certainly the same
real-world role) is recorded as a known, deliberate, not-yet-resolved
alias — not hidden, not auto-merged.

## Consequences

- A single canonical permission-key inventory exists
  (`apps.kernel.permissions`), importable by every app without a
  dependency cycle (kernel sits at the root of the dependency graph).
- No production `PermissionService.require()`/`.check()` call site uses
  an inline string literal (enforced by a guardrail test).
- Four real authorization defects are fixed, each with dedicated
  allow/deny tests proving the fix — three surfaced by the
  centralization work itself, plus the previously tracked reviewer
  ownership gap fixed under this Epic's explicit permission to do so.
- `kernel.Permission` remains dormant — recorded here as a deliberate,
  revisitable decision, not an oversight.
- The two role-seeding commands remain intentionally distinct; their one
  known slug divergence is documented, not resolved, pending a future,
  dedicated, database-safe rename/merge decision.
