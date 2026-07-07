"""Affiliation services — create, approve, reject requests."""

from django.db import transaction
from django.utils import timezone

from ..models.profiles import (
    AffiliationStatus,
    CaregiverProviderType,
    CompanyAffiliationRequest,
    OrganizationMembership,
    OrgMembershipRole,
    OrgMembershipStatus,
)
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
    OrganizationMembership.objects.get_or_create(
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
