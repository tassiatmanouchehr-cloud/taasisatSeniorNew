"""
OrganizationStaffService — Epic 02 (Marketplace Operational Experience).

Read/write operations on OrganizationMembership rows, always scoped to a
specific OrganizationProfile the caller already administers — ownership of
the *organization itself* is verified once, upstream, by
apps.organization_portal.permissions.resolve_organization() before any of
these methods are ever called; this module only adds the second-level
check that a given membership/staff row actually belongs to that same
organization.

OrgMembershipStatus has no distinct "APPROVED" value — approval is
modeled as the existing PENDING -> ACTIVE transition plus the model's own
approved_by/joined_at fields, both already present on OrganizationMembership
since Module 08. Nothing new was added to the model for this.
"""

from .errors import AccountsError


class OrganizationStaffService:
    """Staff (OrganizationMembership) management, scoped to one organization."""

    @classmethod
    def list_staff(cls, organization):
        from ..models.profiles import OrganizationMembership

        return OrganizationMembership.objects.filter(
            organization=organization,
        ).select_related("user", "person").order_by("role_type", "-created_at")

    @classmethod
    def list_active_caregivers(cls, organization):
        from ..models.profiles import OrgMembershipRole, OrgMembershipStatus

        return cls.list_staff(organization).filter(
            role_type=OrgMembershipRole.CAREGIVER, status=OrgMembershipStatus.ACTIVE,
        )

    @classmethod
    def count_staff(cls, organization):
        return cls.list_staff(organization).count()

    @classmethod
    def count_pending_staff(cls, organization):
        from ..models.profiles import OrgMembershipStatus

        return cls.list_staff(organization).filter(status=OrgMembershipStatus.PENDING).count()

    @classmethod
    def get_membership(cls, *, organization, membership_id):
        """Ownership-safe lookup: raises AccountsError if the membership doesn't
        exist or doesn't belong to this organization."""
        from ..models.profiles import OrganizationMembership

        try:
            return OrganizationMembership.objects.get(organization=organization, id=membership_id)
        except OrganizationMembership.DoesNotExist:
            raise AccountsError("Staff member not found.")

    @classmethod
    def approve_membership(cls, membership, *, approved_by=None):
        from django.utils import timezone

        from ..models.profiles import OrgMembershipStatus

        membership.status = OrgMembershipStatus.ACTIVE
        membership.approved_by = approved_by
        membership.joined_at = timezone.now()
        membership.save(update_fields=["status", "approved_by", "joined_at", "updated_at"])
        return membership

    @classmethod
    def suspend_membership(cls, membership):
        from ..models.profiles import OrgMembershipStatus

        membership.status = OrgMembershipStatus.SUSPENDED
        membership.save(update_fields=["status", "updated_at"])
        return membership

    @classmethod
    def resolve_staff_supplier(cls, *, organization, membership_id):
        """Ownership-scoped: only an ACTIVE, CAREGIVER-role member of this
        organization can be resolved to a ServiceSupplier for assignment
        purposes. Raises AccountsError otherwise (unknown membership, wrong
        organization, wrong role, not active, or no provider profile)."""
        from ..models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus
        from .provider_identity import resolve_supplier_for_user

        try:
            membership = OrganizationMembership.objects.get(
                organization=organization, id=membership_id,
                role_type=OrgMembershipRole.CAREGIVER, status=OrgMembershipStatus.ACTIVE,
            )
        except OrganizationMembership.DoesNotExist:
            raise AccountsError("Staff member not found.")

        return resolve_supplier_for_user(membership.user)

    @classmethod
    def list_active_caregiver_supplier_ids(cls, organization):
        """Best-effort: every ACTIVE, CAREGIVER-role member's ServiceSupplier
        id, skipping any member who has no resolvable provider profile
        (never raises — used for read-only dashboards/reports)."""
        from .provider_identity import resolve_supplier_for_user

        supplier_ids = []
        for membership in cls.list_active_caregivers(organization):
            try:
                supplier_ids.append(resolve_supplier_for_user(membership.user).id)
            except AccountsError:
                continue
        return supplier_ids
