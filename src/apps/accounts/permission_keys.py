"""
RBAC permission_key taxonomy for organization-isolation enforcement points —
Epic 04 (Enterprise Organization Isolation), corrected in Epic 05
(Permission-Key Registry & Authorization Hardening).

Epic 05 correction: `ORGANIZATION_ASSIGNMENT_ASSIGN =
"organization.assignment.assign"` was retired — it was never actually
checked anywhere. `AssignmentService.assign()` checks the literal
`"booking.assignment.assign"` regardless of the `scope` kwarg passed to
it; `scope` only narrows *which* RoleAssignment can satisfy that one
existing key, it never introduces a second key. Granting
`organization_admin` a key nothing ever checks meant the role's "real
RBAC" path never actually activated — every assign_manual() call kept
silently falling through to the ownership_authorized_by audit trail
instead. `BOOKING_ASSIGNMENT_ASSIGN` (re-exported below, canonical
definition in apps.kernel.permissions.keys, owned by apps.booking's own
enforcement point) is the correct key going forward. See
docs/adr/ADR-010_CANONICAL_PERMISSION_REGISTRY.md for the full writeup of
this defect and its fix.

This module is now a re-export facade over the canonical registry
(apps.kernel.permissions.keys) — the two remaining keys' values and local
names are unchanged; only registration/metadata/duplicate-detection moved
to one place.

Located in apps.accounts (not apps.booking or apps.orders, both of which
also enforce against these keys) because apps.accounts is the most
upstream of the three consuming apps in the dependency graph
(kernel -> accounts -> orders -> booking) — apps.orders and apps.booking
importing from apps.accounts does not invert that graph; the reverse would.

Do not add a key without a real PermissionService.require() call site to
back it; apps.organization_portal.permissions.resolve_organization()
already gates every organization-portal view to an ACTIVE, ADMIN-role
OrganizationMembership, so no other OrgMembershipRole value has an
enforcement point to hold a permission for in this Epic.

Epic 06 Sprint 2: `ORGANIZATION_PROFILE_UPDATE` added, guarding
`OrganizationProfileUpdateService.update_profile()` — same
ownership-fallback shape as `ORGANIZATION_MEMBERSHIP_APPROVE`/`_SUSPEND`.
"""

from apps.kernel.permissions.keys import (
    BOOKING_ASSIGNMENT_ASSIGN,
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_SUSPEND,
    ORGANIZATION_PROFILE_UPDATE,
)

__all__ = [
    "BOOKING_ASSIGNMENT_ASSIGN",
    "ORGANIZATION_MEMBERSHIP_APPROVE",
    "ORGANIZATION_MEMBERSHIP_SUSPEND",
    "ORGANIZATION_PROFILE_UPDATE",
]
