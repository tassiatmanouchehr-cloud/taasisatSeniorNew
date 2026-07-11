"""
OrganizationProfileUpdateService — Epic 06 Sprint 2 (Shared Portal UI
Core, Provider Profile, Organization Profile).

Mirrors `apps.accounts.services.organization_staff.OrganizationStaffService
.approve_membership()`'s exact authorization shape: a real actor is tried
first against the canonical `ORGANIZATION_PROFILE_UPDATE` permission key,
falling back to an audited ownership-authorized entry only if no scoped
RoleAssignment exists yet for that actor — never a silent bypass, never a
lockout. `actor` is expected to already be the caller's own
`request.user`, already resolved to administer this organization by
`apps.organization_portal.permissions.resolve_organization()` upstream —
this service does not re-derive "does this user own this organization,"
it only re-verifies the RBAC/ownership grant, per this codebase's
established `ownership_authorized_by` contract (see
`docs/architecture/rbac-permissions.md`).

Field-whitelisted for the same reason `CaregiverProfileUpdateService` is:
one fixed field set, no generic `**kwargs` mass-assignment path. Never
touches `verification_status`, `status`, `code`, `admin_user`, or
`tenant`.
"""

from django.db import transaction

from apps.kernel.permissions.keys import ORGANIZATION_PROFILE_UPDATE
from apps.kernel.services.permission_service import PermissionService
from apps.kernel.services.supplier_registry import SupplierRegistry

from .supplier_bridge import get_or_create_supplier_for_organization


class OrganizationProfileUpdateService:
    """Read-write: an organization's own editable public/contact fields."""

    @classmethod
    @transaction.atomic
    def update_profile(
        cls,
        organization,
        *,
        actor,
        name: str,
        description: str,
        city: str,
        phone: str,
        address: str,
        company_type: str = "",
        team_size: str = "",
    ):
        PermissionService.require(
            None,
            ORGANIZATION_PROFILE_UPDATE,
            tenant_id=organization.tenant_id,
            ownership_authorized_by=actor,
            scope={"scope_type": "organization", "scope_id": str(organization.id)},
        )

        organization.name = (name or "").strip()
        organization.description = (description or "").strip()
        organization.city = (city or "").strip()
        organization.phone = (phone or "").strip()
        organization.address = (address or "").strip()
        organization.company_type = (company_type or "").strip()
        organization.team_size = (team_size or "").strip()
        organization.save(
            update_fields=[
                "name",
                "description",
                "city",
                "phone",
                "address",
                "company_type",
                "team_size",
                "updated_at",
            ],
        )
        return organization

    @classmethod
    @transaction.atomic
    def update_service_categories(cls, organization, *, actor, service_category_ids: list[str]):
        PermissionService.require(
            None,
            ORGANIZATION_PROFILE_UPDATE,
            tenant_id=organization.tenant_id,
            ownership_authorized_by=actor,
            scope={"scope_type": "organization", "scope_id": str(organization.id)},
        )
        supplier = get_or_create_supplier_for_organization(organization, tenant_id=organization.tenant_id)
        SupplierRegistry.set_service_categories(supplier, service_category_ids=service_category_ids)
        return organization
