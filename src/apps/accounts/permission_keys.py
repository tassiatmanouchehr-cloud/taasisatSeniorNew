"""
RBAC permission_key taxonomy for organization-isolation enforcement points —
Epic 04 (Enterprise Organization Isolation).

Follows the same convention as apps.api.permission_keys and
apps.admin_portal.permission_keys (documented in
docs/architecture/rbac-permissions.md): `<domain>.<resource>.<action>`,
lowercase, dot-separated. No permission_key registry exists anywhere in the
platform (Role.permissions is a freeform JSON string list — see
apps.kernel.models.rbac); these constants exist so keys aren't scattered as
magic strings across service modules. Roles must be granted these keys
explicitly — nothing here auto-grants access to any role.

Located in apps.accounts (not apps.booking or apps.orders, both of which
also enforce against these keys) because apps.accounts is the most
upstream of the three consuming apps in the dependency graph
(kernel -> accounts -> orders -> booking) — apps.orders and apps.booking
importing from apps.accounts does not invert that graph; the reverse would.

Only three keys exist because only three enforcement points were planned
for this Epic's approved scope — see each key's docstring for its current,
actual enforcement status. Do not add a key without a real
PermissionService.require() call site to back it;
apps.organization_portal.permissions.resolve_organization() already gates
every organization-portal view to an ACTIVE, ADMIN-role
OrganizationMembership, so no other OrgMembershipRole value has an
enforcement point to hold a permission for in this Epic.

Architecture Review remediation (Epic 04, PR #28 required remediation item
2): all three keys below are defined and are granted to the
organization_admin Role (apps.accounts.services.organization_rbac
.ORGANIZATION_ADMIN_PERMISSIONS, seeded by
apps.accounts.management.commands.seed_auth_roles), but as of this Epic
NONE of them is actually consulted by a PermissionService.require()/.check()
call anywhere in the codebase — verified by direct inspection, not
assumed. Every organization-admin action these keys were intended to guard
is, today, authorized entirely through PermissionService.require()'s
pre-existing ownership_authorized_by fallback (an already-verified,
correctly tenant/organization-scoped actor — never an open bypass, never
mislabeled as system context — see that method's own docstring), not
through a real RoleAssignment check against one of these keys. This is a
deliberate, tracked, temporary limitation of this Epic, not a security
gap: closing it (wiring these call sites to check their intended key) is
Permission-Key Registry & Authorization Hardening (Epic 05) scope, not
this Epic's.
"""

ORGANIZATION_ASSIGNMENT_ASSIGN = "organization.assignment.assign"
"""Intended to guard: apps.booking.services.assignment_service
.AssignmentService.assign(), when called with a
scope={"scope_type": "organization", ...} kwarg — the path
apps.booking.services.organization_assignment
.OrganizationAssignmentService.assign_manual() always uses.

NOT YET ENFORCED (this Epic): assign() checks the literal string
"booking.assignment.assign", not this key — the two are different
strings and never match, so a RoleAssignment carrying this key never
authorizes the call via a real permission check. assign_manual() remains
safe because it passes ownership_authorized_by=actor, so every call is
still authorized via the ownership fallback. See this module's own
docstring."""

ORGANIZATION_MEMBERSHIP_APPROVE = "organization.membership.approve"
"""Intended to guard: apps.accounts.services.organization_staff
.OrganizationStaffService.approve_membership().

NOT YET ENFORCED (this Epic): approve_membership() contains no
PermissionService.require()/.check() call of any kind. The method remains
safe because every caller reaches it only through
apps.organization_portal.permissions.resolve_organization(), which gates
every organization-portal view to the caller's own ACTIVE, ADMIN-role
OrganizationMembership before this method is ever invoked. See this
module's own docstring."""

ORGANIZATION_MEMBERSHIP_SUSPEND = "organization.membership.suspend"
"""Intended to guard: apps.accounts.services.organization_staff
.OrganizationStaffService.suspend_membership().

NOT YET ENFORCED (this Epic): suspend_membership() contains no
PermissionService.require()/.check() call of any kind — same status and
same reasoning as ORGANIZATION_MEMBERSHIP_APPROVE above."""
