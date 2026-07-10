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

Only three keys exist because only three enforcement points exist in this
Epic's approved scope — see each key's docstring for its exact call site.
Do not add a key without a real PermissionService.require() call site to
back it; apps.organization_portal.permissions.resolve_organization()
already gates every organization-portal view to an ACTIVE, ADMIN-role
OrganizationMembership, so no other OrgMembershipRole value has an
enforcement point to hold a permission for in this Epic.
"""

ORGANIZATION_ASSIGNMENT_ASSIGN = "organization.assignment.assign"
"""Guards: apps.booking.services.assignment_service.AssignmentService.assign(),
when called with a scope={"scope_type": "organization", ...} kwarg — the
path apps.booking.services.organization_assignment
.OrganizationAssignmentService.assign_manual() always uses."""

ORGANIZATION_MEMBERSHIP_APPROVE = "organization.membership.approve"
"""Guards: apps.accounts.services.organization_staff.OrganizationStaffService
.approve_membership()."""

ORGANIZATION_MEMBERSHIP_SUSPEND = "organization.membership.suspend"
"""Guards: apps.accounts.services.organization_staff.OrganizationStaffService
.suspend_membership()."""
