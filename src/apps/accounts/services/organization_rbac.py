"""
OrganizationRoleSyncService — Epic 04 (Enterprise Organization Isolation).

The sole writer of organization-scoped RoleAssignment rows
(scope_type="organization"). Activates the RBAC scope machinery that
already existed but had no writer: apps.kernel.services.permission_service
.PermissionService._scope_matches() has correctly evaluated
scope_type/scope_id since Module 08 — this service is what finally creates
the rows for it to evaluate.

Only OrgMembershipRole.ADMIN is synced to a RoleAssignment in this Epic.
apps.organization_portal.permissions.resolve_organization() already gates
every organization-portal view to an ACTIVE, ADMIN-role
OrganizationMembership — no other role_type has any enforcement point to
hold a permission for yet, so syncing one would create a RoleAssignment
nothing ever checks. A future Epic that opens portal views to other
role_types extends the mapping table below, not this method's contract.

Hook points (the only two places an ADMIN-role OrganizationMembership
transitions status in this codebase today):
- apps.accounts.services.affiliations.approve_affiliation_request()
  (caregiver-initiated flow — does not touch ADMIN memberships in
  practice, but the hook is generic and correct if it ever did)
- apps.accounts.services.organization_staff.OrganizationStaffService
  .approve_membership() / .suspend_membership()

No flag-day lockout: apps.booking.services.assignment_service
.AssignmentService.assign()'s ownership_authorized_by fallback (see that
module's docstring) is tried only after the real permission check fails —
an admin whose sync hasn't run yet (e.g. mid-backfill) is never locked
out, they just fall back to the same ownership-authorized path used before
this Epic existed.
"""

from django.db import transaction

from apps.accounts.permission_keys import (
    BOOKING_ASSIGNMENT_ASSIGN,
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_SUSPEND,
)
from apps.kernel.models.rbac import Role, RoleAssignment
from apps.kernel.services.audit_service import AuditService

from ..models.profiles import OrgMembershipRole, OrgMembershipStatus

ORGANIZATION_ADMIN_ROLE_SLUG = "organization_admin"
ORGANIZATION_ADMIN_ROLE_NAME = "مدیر سازمان"
ORGANIZATION_ADMIN_PERMISSIONS = [
    BOOKING_ASSIGNMENT_ASSIGN,
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_SUSPEND,
]

SOURCE_MODULE = "M26"

# See module docstring for why only ADMIN is synced in this Epic.
_SYNCED_ROLE_TYPES = {OrgMembershipRole.ADMIN}


class OrganizationRoleSyncError(Exception):
    pass


class OrganizationRoleSyncService:
    """Idempotently mirrors an OrganizationMembership's status into a
    scoped RoleAssignment. See module docstring for scope (ADMIN only)."""

    @classmethod
    def _resolve_role(cls, *, tenant) -> Role:
        """Idempotent get-or-create, then an additive permissions merge —
        mirrors apps.kernel.management.commands.seed_tenant's own
        missing_permissions pattern so a role created before this Epic's
        permission list existed still ends up with every required key,
        without ever removing a tenant-customized addition."""
        role, _ = Role.objects.get_or_create(
            tenant=tenant, slug=ORGANIZATION_ADMIN_ROLE_SLUG,
            defaults={"name": ORGANIZATION_ADMIN_ROLE_NAME, "is_system": True, "permissions": list(ORGANIZATION_ADMIN_PERMISSIONS)},
        )
        missing = [key for key in ORGANIZATION_ADMIN_PERMISSIONS if key not in role.permissions]
        if missing:
            role.permissions = [*role.permissions, *missing]
            role.save(update_fields=["permissions", "updated_at", "version"])
        return role

    @classmethod
    def _validate_tenant_consistency(cls, membership) -> None:
        organization_tenant_id = membership.organization.tenant_id
        user_tenant_id = membership.user.tenant_id
        if organization_tenant_id is None:
            raise OrganizationRoleSyncError("Organization has no tenant; cannot sync role assignment.")
        if user_tenant_id is None:
            raise OrganizationRoleSyncError("User has no tenant; cannot sync role assignment.")
        if organization_tenant_id != user_tenant_id:
            raise OrganizationRoleSyncError("Organization tenant does not match member's tenant.")

    @classmethod
    @transaction.atomic
    def sync_for_membership(cls, membership) -> RoleAssignment | None:
        """Returns the synced RoleAssignment, or None if this membership's
        role_type is not synced in this Epic (see module docstring)."""
        if membership.role_type not in _SYNCED_ROLE_TYPES:
            return None

        cls._validate_tenant_consistency(membership)
        tenant_id = membership.organization.tenant_id
        role = cls._resolve_role(tenant=membership.organization.tenant)

        should_be_active = membership.status == OrgMembershipStatus.ACTIVE

        granted_by_person_id = membership.approved_by.person_id if membership.approved_by_id else None
        assignment, created = RoleAssignment.objects.select_for_update().get_or_create(
            tenant_id=tenant_id, user=membership.user, role=role,
            scope_type="organization", scope_id=membership.organization_id,
            defaults={"is_active": should_be_active, "granted_by": granted_by_person_id},
        )
        if assignment.is_active != should_be_active:
            assignment.is_active = should_be_active
            assignment.save(update_fields=["is_active"])

        cls._audit(membership=membership, assignment=assignment, created=created, is_active=should_be_active)
        return assignment

    @classmethod
    def _audit(cls, *, membership, assignment, created, is_active) -> None:
        action = "organization.role_assignment.created" if created else (
            "organization.role_assignment.activated" if is_active else "organization.role_assignment.deactivated"
        )
        AuditService.log(
            tenant_id=assignment.tenant_id,
            action=action,
            resource_type="RoleAssignment",
            resource_id=assignment.id,
            module_id=SOURCE_MODULE,
            actor_id=membership.approved_by.person_id if membership.approved_by_id else None,
            actor_type="user" if membership.approved_by_id else "system",
            after={
                "user_id": str(membership.user_id),
                "role_slug": assignment.role.slug,
                "scope_type": assignment.scope_type,
                "scope_id": str(assignment.scope_id),
            },
        )
