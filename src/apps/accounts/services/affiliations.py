"""Affiliation services — create, approve, reject requests.

Epic 04 (Enterprise Organization Isolation): approve_affiliation_request()
now also calls OrganizationRoleSyncService.sync_for_membership() in the
same atomic block as the membership get_or_create() — a no-op today (this
flow only ever creates CAREGIVER-role_type memberships, which are not
synced to a RoleAssignment in this Epic — see that service's module
docstring), but correct and future-proof if this flow is ever extended to
create an ADMIN membership."""

from django.db import transaction
from django.utils import timezone

from apps.kernel.services.audit_service import AuditService

from ..models.profiles import (
    AffiliationStatus,
    CaregiverProviderType,
    CompanyAffiliationRequest,
    OrganizationMembership,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from .organization_rbac import OrganizationRoleSyncService
from .organizations import find_organization_by_code_or_name


def create_affiliation_request(*, caregiver_profile, company_ref, caregiver_note=""):
    """Create a pending affiliation request. Tries to resolve org by code/name."""
    organization = find_organization_by_code_or_name(company_ref)
    request = CompanyAffiliationRequest.objects.create(
        caregiver_profile=caregiver_profile,
        requested_company_name_or_code=company_ref,
        organization=organization,
        caregiver_note=caregiver_note,
    )
    return request


@transaction.atomic
def approve_affiliation_request(*, request_id, reviewed_by, reviewer_note=""):
    """
    Approve an affiliation request.

    - Request must be pending
    - Organization must be resolved
    - Caregiver becomes organization_affiliated
    - Creates active OrganizationMembership
    """
    req = CompanyAffiliationRequest.objects.select_for_update().get(id=request_id)

    if req.status != AffiliationStatus.PENDING:
        raise ValueError("Only pending requests can be approved.")
    if not req.organization:
        raise ValueError("Cannot approve: organization not resolved.")
    if req.organization.tenant_id is None:
        raise ValueError("Cannot approve: organization has no tenant.")

    # Update request
    req.status = AffiliationStatus.APPROVED
    req.reviewed_by = reviewed_by
    req.reviewed_at = timezone.now()
    req.reviewer_note = reviewer_note
    req.save()

    # Update caregiver provider_type
    profile = req.caregiver_profile
    profile.provider_type = CaregiverProviderType.ORGANIZATION_AFFILIATED
    profile.save(update_fields=["provider_type", "updated_at"])

    # Create membership
    membership, _ = OrganizationMembership.objects.get_or_create(
        organization=req.organization,
        user=profile.user,
        role_type=OrgMembershipRole.CAREGIVER,
        defaults={
            "person": profile.person,
            "status": OrgMembershipStatus.ACTIVE,
            "approved_by": reviewed_by,
            "joined_at": timezone.now(),
        },
    )
    OrganizationRoleSyncService.sync_for_membership(membership)
    AuditService.log(
        tenant_id=req.organization.tenant_id,
        action="organization.membership.approved",
        resource_type="OrganizationMembership",
        resource_id=membership.id,
        module_id="M26",
        actor_id=reviewed_by.person_id if reviewed_by else None,
        actor_type="user" if reviewed_by else "system",
        after={"organization_id": str(req.organization_id), "user_id": str(membership.user_id), "role_type": membership.role_type},
    )

    return req


@transaction.atomic
def reject_affiliation_request(*, request_id, reviewed_by, reviewer_note=""):
    """
    Reject an affiliation request.

    - Request must be pending
    - Caregiver remains independent
    """
    req = CompanyAffiliationRequest.objects.select_for_update().get(id=request_id)

    if req.status != AffiliationStatus.PENDING:
        raise ValueError("Only pending requests can be rejected.")

    req.status = AffiliationStatus.REJECTED
    req.reviewed_by = reviewed_by
    req.reviewed_at = timezone.now()
    req.reviewer_note = reviewer_note
    req.save()

    return req
