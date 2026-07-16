"""Affiliation services — the caregiver-company relationship lifecycle.

Epic 04 (Enterprise Organization Isolation): approve_affiliation_request()
now also calls OrganizationRoleSyncService.sync_for_membership() in the
same atomic block as the membership get_or_create() — a no-op today (this
flow only ever creates CAREGIVER-role_type memberships, which are not
synced to a RoleAssignment in this Epic — see that service's module
docstring), but correct and future-proof if this flow is ever extended to
create an ADMIN membership.

Phase 3 Sprint 3.1 (Company Foundation and Caregiver Management): extends
this module (rather than adding new service classes — see ADM entry for
this sprint) to cover the full affiliation lifecycle across the two
existing models:

- `CompanyAffiliationRequest` — the caregiver-initiated "join by code"
  intake record. REQUESTED -> ACTIVE (approve_affiliation_request) or
  REQUESTED -> REJECTED (reject_affiliation_request) or REQUESTED ->
  CANCELLED (cancel_affiliation_request, caregiver-initiated withdrawal).
- `OrganizationMembership` — the single canonical, historical,
  organization+caregiver relationship record, for BOTH the join-by-code
  path (created ACTIVE the moment a request is approved) and the new
  company-initiated invitation path (created PENDING with `invited_by`
  set; the caregiver then accepts or declines). ACTIVE -> TERMINATED by
  either side (terminate_membership()/leave_organization()). Because
  `unique_together = [("organization", "user", "role_type")]` allows at
  most one row per (org, caregiver) pair, a caregiver who leaves and later
  rejoins the *same* organization reactivates that same row rather than
  getting a second one — full cross-cycle history for that case lives in
  AuditLog (via AuditService.log()), not on the row itself; the row always
  reflects the current/latest cycle. See ARCHITECTURE_DECISION_LOG.md's
  Sprint 3.1 entry.

One-active-company-at-a-time is this sprint's deliberate, minimal policy
(see the same ADM entry): `CaregiverProfile.provider_type` is a scalar,
not a set, and no other part of this codebase resolves a caregiver to
more than one organization at once. `_assert_no_active_membership()`
enforces this at the service layer (not a DB constraint, since it must
hold across different `organization` values, which the unique_together
above does not cover) — every caller locks the caregiver's own
CaregiverProfile row (the one stable "parent" every activation path
shares, regardless of which organization/request/invitation is involved)
via `select_for_update()` *before* calling it, mirroring
`CaregiverGalleryService.add_item()`'s and `AvailabilityMutationService
.add_working_window()`'s existing "lock the owning parent, then
check-then-write" precedent for the same class of problem: two different
`CompanyAffiliationRequest`/`OrganizationMembership` rows (one per
organization) share no lockable row of their own, so without this the
same caregiver could be raced into two simultaneously-ACTIVE memberships
at two different organizations."""

from django.db import transaction
from django.utils import timezone

from apps.kernel.permissions.keys import (
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_INVITE,
    ORGANIZATION_MEMBERSHIP_REJECT,
    ORGANIZATION_MEMBERSHIP_TERMINATE,
)
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models.profiles import (
    AffiliationStatus,
    CaregiverProfile,
    CaregiverProviderType,
    CompanyAffiliationRequest,
    OrganizationMembership,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from .errors import AccountsError
from .organization_rbac import OrganizationRoleSyncService
from .organizations import find_organization_by_code_or_name

MODULE_ID = "M26"


def _assert_no_active_membership(*, user, exclude_membership_id=None) -> None:
    """One active company affiliation per caregiver at a time (this
    sprint's documented minimal policy — see module docstring)."""
    active = OrganizationMembership.objects.filter(user=user, status=OrgMembershipStatus.ACTIVE)
    if exclude_membership_id:
        active = active.exclude(id=exclude_membership_id)
    if active.exists():
        raise AccountsError("This caregiver already has an active company affiliation.")


def _resolve_join_code_organization(*, code, tenant_id):
    """Tenant-scoped, exact-code-only resolution for the public join-code
    flow (Section D) — deliberately narrower than
    find_organization_by_code_or_name()'s legacy code-or-name lookup
    (that function's loose `name__icontains` fallback is not safe for a
    caregiver-facing "enter your company's code" flow, and it is not
    tenant-scoped — see this sprint's own governance and the ADM entry).
    Only an ACTIVE organization profile is joinable; DRAFT/SUSPENDED/
    ARCHIVED companies never resolve, so their code is silently unusable
    (never a distinct error message that could leak the company's
    lifecycle state)."""
    from ..models.profiles import OrganizationProfile, ProfileStatus

    code = (code or "").strip()
    if not code:
        return None
    return OrganizationProfile.objects.filter(
        code__iexact=code, tenant_id=tenant_id, status=ProfileStatus.ACTIVE,
    ).first()


# ============================================================
# Caregiver-initiated: join-by-code request
# ============================================================


def create_affiliation_request(*, caregiver_profile, company_ref, caregiver_note=""):
    """Create a pending affiliation request. Tries to resolve org by code/name.

    Legacy entry point (registration-time company_code/company_name
    fields) — kept exactly as-is for RegistrationService.create_caregiver()
    and any other existing caller. The new join-code portal flow
    (Section D) uses submit_join_request() below instead, which is
    tenant-scoped and code-only."""
    organization = find_organization_by_code_or_name(company_ref)
    request = CompanyAffiliationRequest.objects.create(
        caregiver_profile=caregiver_profile,
        requested_company_name_or_code=company_ref,
        organization=organization,
        caregiver_note=caregiver_note,
    )
    return request


def submit_join_request(*, caregiver_profile, code, tenant_id, caregiver_note=""):
    """The provider_portal join-code flow's entry point (Section D):
    tenant-scoped, exact-code, ACTIVE-organization-only resolution, with
    the safety checks a public code-entry surface needs — refuses a
    second pending request/active membership, never leaks *why* a code
    didn't resolve (unknown code and an inactive company's code both look
    identical to the caregiver)."""
    if OrganizationMembership.objects.filter(
        user=caregiver_profile.user, status=OrgMembershipStatus.ACTIVE,
    ).exists():
        raise AccountsError("This caregiver already has an active company affiliation.")
    if CompanyAffiliationRequest.objects.filter(
        caregiver_profile=caregiver_profile, status=AffiliationStatus.PENDING,
    ).exists():
        raise AccountsError("A join request is already pending.")

    organization = _resolve_join_code_organization(code=code, tenant_id=tenant_id)
    if organization is None:
        raise AccountsError("Invalid company code.")

    return CompanyAffiliationRequest.objects.create(
        caregiver_profile=caregiver_profile,
        requested_company_name_or_code=code,
        organization=organization,
        caregiver_note=caregiver_note,
    )


def preview_join_code_organization(*, code, tenant_id):
    """Read-only: resolves a code to the organization's public-safe
    display fields only (name, city), for the "confirm this is the
    company you want to join" step — never the full OrganizationProfile,
    never private fields (registration_number, address, phone,
    verification_status). Returns None for an invalid or inactive code,
    identically to submit_join_request()'s own resolution."""
    organization = _resolve_join_code_organization(code=code, tenant_id=tenant_id)
    if organization is None:
        return None
    return {"id": organization.id, "name": organization.name, "city": organization.city}


@transaction.atomic
def cancel_affiliation_request(*, request_id, caregiver_profile):
    """Caregiver-owned: withdraw one's own still-pending request.
    Ownership-authorized (matches every other caregiver-self-service
    action in this codebase), never RBAC-gated."""
    req = CompanyAffiliationRequest.objects.select_for_update().get(id=request_id)
    if req.caregiver_profile_id != caregiver_profile.id:
        raise AccountsError("This affiliation request does not belong to this caregiver.")
    if req.status != AffiliationStatus.PENDING:
        raise AccountsError("Only pending requests can be cancelled.")

    req.status = AffiliationStatus.CANCELLED
    req.reviewed_at = timezone.now()
    req.save(update_fields=["status", "reviewed_at"])
    return req


# ============================================================
# Company-initiated: review a join-by-code request
# ============================================================


@transaction.atomic
def approve_affiliation_request(*, request_id, reviewed_by, reviewer_note=""):
    """
    Approve an affiliation request.

    - Request must be pending
    - Organization must be resolved
    - Caregiver becomes organization_affiliated
    - Creates/reactivates an active OrganizationMembership
    """
    req = CompanyAffiliationRequest.objects.select_for_update().get(id=request_id)

    if req.status != AffiliationStatus.PENDING:
        raise AccountsError("Only pending requests can be approved.")
    if not req.organization:
        raise AccountsError("Cannot approve: organization not resolved.")
    if req.organization.tenant_id is None:
        raise AccountsError("Cannot approve: organization has no tenant.")

    PermissionService.require(
        None, ORGANIZATION_MEMBERSHIP_APPROVE, tenant_id=req.organization.tenant_id,
        ownership_authorized_by=reviewed_by,
        scope={"scope_type": "organization", "scope_id": str(req.organization_id)},
    )

    # Lock the caregiver's own profile row first — the stable parent every
    # activation path (join-request approval, invitation acceptance)
    # shares, closing the race two different organizations' request/
    # invitation rows (which share no lock of their own) would otherwise
    # allow. See module docstring.
    profile = CaregiverProfile.objects.select_for_update().get(id=req.caregiver_profile_id)
    _assert_no_active_membership(user=profile.user)

    # Update request
    req.status = AffiliationStatus.APPROVED
    req.reviewed_by = reviewed_by
    req.reviewed_at = timezone.now()
    req.reviewer_note = reviewer_note
    req.save()

    # Update caregiver provider_type
    profile.provider_type = CaregiverProviderType.ORGANIZATION_AFFILIATED
    profile.save(update_fields=["provider_type", "updated_at"])

    # Create/reactivate membership — update_or_create (not get_or_create) so a
    # caregiver rejoining the same organization after a prior termination
    # reactivates that same row (unique_together permits only one row per
    # organization+user+role_type) rather than raising IntegrityError.
    membership, _ = OrganizationMembership.objects.update_or_create(
        organization=req.organization,
        user=profile.user,
        role_type=OrgMembershipRole.CAREGIVER,
        defaults={
            "person": profile.person,
            "status": OrgMembershipStatus.ACTIVE,
            "approved_by": reviewed_by,
            "joined_at": timezone.now(),
            "terminated_at": None,
            "terminated_by": None,
            "termination_reason": "",
        },
    )
    OrganizationRoleSyncService.sync_for_membership(membership)
    AuditService.log(
        tenant_id=req.organization.tenant_id,
        action="organization.membership.approved",
        resource_type="OrganizationMembership",
        resource_id=membership.id,
        module_id=MODULE_ID,
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
        raise AccountsError("Only pending requests can be rejected.")

    if req.organization:
        PermissionService.require(
            None, ORGANIZATION_MEMBERSHIP_REJECT, tenant_id=req.organization.tenant_id,
            ownership_authorized_by=reviewed_by,
            scope={"scope_type": "organization", "scope_id": str(req.organization_id)},
        )

    req.status = AffiliationStatus.REJECTED
    req.reviewed_by = reviewed_by
    req.reviewed_at = timezone.now()
    req.reviewer_note = reviewer_note
    req.save()

    return req


# ============================================================
# Company-initiated: invite a specific caregiver
# ============================================================


@transaction.atomic
def invite_caregiver(*, organization, caregiver_phone, invited_by):
    """Company-initiated invitation: creates (or reactivates) a PENDING
    OrganizationMembership with invited_by set. The caregiver must accept
    (accept_invitation()) before it becomes ACTIVE — never auto-activated."""
    if organization.tenant_id is None:
        raise AccountsError("Cannot invite: organization has no tenant.")

    PermissionService.require(
        None, ORGANIZATION_MEMBERSHIP_INVITE, tenant_id=organization.tenant_id,
        ownership_authorized_by=invited_by,
        scope={"scope_type": "organization", "scope_id": str(organization.id)},
    )

    try:
        # Lock the caregiver's own profile row first — see module docstring.
        caregiver = CaregiverProfile.objects.select_for_update().select_related("user", "person").get(
            phone=caregiver_phone,
        )
    except CaregiverProfile.DoesNotExist:
        raise AccountsError("No caregiver found with this phone number.") from None

    _assert_no_active_membership(user=caregiver.user)
    existing = OrganizationMembership.objects.filter(
        organization=organization, user=caregiver.user, role_type=OrgMembershipRole.CAREGIVER,
    ).first()
    if existing and existing.status == OrgMembershipStatus.PENDING:
        raise AccountsError("This caregiver already has a pending invitation or request.")

    membership, _ = OrganizationMembership.objects.update_or_create(
        organization=organization,
        user=caregiver.user,
        role_type=OrgMembershipRole.CAREGIVER,
        defaults={
            "person": caregiver.person,
            "status": OrgMembershipStatus.PENDING,
            "invited_by": invited_by,
            "approved_by": None,
            "joined_at": None,
            "terminated_at": None,
            "terminated_by": None,
            "termination_reason": "",
        },
    )
    AuditService.log(
        tenant_id=organization.tenant_id,
        action="organization.membership.invited",
        resource_type="OrganizationMembership",
        resource_id=membership.id,
        module_id=MODULE_ID,
        actor_id=invited_by.person_id if invited_by else None,
        actor_type="user" if invited_by else "system",
        after={"organization_id": str(organization.id), "user_id": str(membership.user_id)},
    )
    return membership


@transaction.atomic
def cancel_invitation(*, membership_id, cancelled_by):
    """Company-side: withdraw an invitation the caregiver has not yet
    responded to. Never touches an invitation the caregiver already
    accepted (must use terminate_membership() for that)."""
    membership = OrganizationMembership.objects.select_for_update().get(id=membership_id)
    if membership.status != OrgMembershipStatus.PENDING or membership.invited_by_id is None:
        raise AccountsError("Only a pending invitation can be cancelled.")

    PermissionService.require(
        None, ORGANIZATION_MEMBERSHIP_REJECT, tenant_id=membership.organization.tenant_id,
        ownership_authorized_by=cancelled_by,
        scope={"scope_type": "organization", "scope_id": str(membership.organization_id)},
    )

    membership.status = OrgMembershipStatus.REMOVED
    membership.terminated_at = timezone.now()
    membership.terminated_by = cancelled_by
    membership.termination_reason = "Invitation cancelled by organization."
    membership.save(update_fields=["status", "terminated_at", "terminated_by", "termination_reason", "updated_at"])

    AuditService.log(
        tenant_id=membership.organization.tenant_id,
        action="organization.membership.invitation_cancelled",
        resource_type="OrganizationMembership",
        resource_id=membership.id,
        module_id=MODULE_ID,
        actor_id=cancelled_by.person_id if cancelled_by else None,
        actor_type="user" if cancelled_by else "system",
        after={"organization_id": str(membership.organization_id), "user_id": str(membership.user_id)},
    )
    return membership


# ============================================================
# Caregiver-initiated: respond to an invitation
# ============================================================


@transaction.atomic
def accept_invitation(*, membership_id, caregiver_profile):
    """Caregiver-owned: accept a pending invitation. Ownership-authorized,
    never RBAC-gated (mirrors every other caregiver-self-service action)."""
    membership = OrganizationMembership.objects.select_for_update().get(id=membership_id)
    if membership.user_id != caregiver_profile.user_id:
        raise AccountsError("This invitation does not belong to this caregiver.")
    if membership.status != OrgMembershipStatus.PENDING or membership.invited_by_id is None:
        raise AccountsError("Only a pending invitation can be accepted.")

    # Lock the caregiver's own profile row first — see module docstring.
    caregiver_profile = CaregiverProfile.objects.select_for_update().get(id=caregiver_profile.id)
    _assert_no_active_membership(user=caregiver_profile.user, exclude_membership_id=membership.id)

    membership.status = OrgMembershipStatus.ACTIVE
    membership.joined_at = timezone.now()
    membership.save(update_fields=["status", "joined_at", "updated_at"])

    caregiver_profile.provider_type = CaregiverProviderType.ORGANIZATION_AFFILIATED
    caregiver_profile.save(update_fields=["provider_type", "updated_at"])

    OrganizationRoleSyncService.sync_for_membership(membership)
    AuditService.log(
        tenant_id=membership.organization.tenant_id,
        action="organization.membership.invitation_accepted",
        resource_type="OrganizationMembership",
        resource_id=membership.id,
        module_id=MODULE_ID,
        actor_id=caregiver_profile.person_id,
        actor_type="user",
        after={"organization_id": str(membership.organization_id), "user_id": str(membership.user_id)},
    )
    return membership


@transaction.atomic
def decline_invitation(*, membership_id, caregiver_profile):
    """Caregiver-owned: decline a pending invitation."""
    membership = OrganizationMembership.objects.select_for_update().get(id=membership_id)
    if membership.user_id != caregiver_profile.user_id:
        raise AccountsError("This invitation does not belong to this caregiver.")
    if membership.status != OrgMembershipStatus.PENDING or membership.invited_by_id is None:
        raise AccountsError("Only a pending invitation can be declined.")

    membership.status = OrgMembershipStatus.REMOVED
    membership.terminated_at = timezone.now()
    membership.terminated_by = caregiver_profile.user
    membership.termination_reason = "Invitation declined by caregiver."
    membership.save(update_fields=["status", "terminated_at", "terminated_by", "termination_reason", "updated_at"])
    return membership


# ============================================================
# Termination (either side, on an ACTIVE membership)
# ============================================================


@transaction.atomic
def terminate_membership(*, membership_id, terminated_by, reason=""):
    """Company-side termination of an ACTIVE membership."""
    membership = OrganizationMembership.objects.select_for_update().get(id=membership_id)
    if membership.status != OrgMembershipStatus.ACTIVE:
        raise AccountsError("Only an active membership can be terminated.")

    PermissionService.require(
        None, ORGANIZATION_MEMBERSHIP_TERMINATE, tenant_id=membership.organization.tenant_id,
        ownership_authorized_by=terminated_by,
        scope={"scope_type": "organization", "scope_id": str(membership.organization_id)},
    )

    _finalize_termination(membership, terminated_by=terminated_by, reason=reason or "Terminated by organization.")

    AuditService.log(
        tenant_id=membership.organization.tenant_id,
        action="organization.membership.terminated",
        resource_type="OrganizationMembership",
        resource_id=membership.id,
        module_id=MODULE_ID,
        actor_id=terminated_by.person_id if terminated_by else None,
        actor_type="user" if terminated_by else "system",
        after={"organization_id": str(membership.organization_id), "user_id": str(membership.user_id)},
    )
    return membership


@transaction.atomic
def leave_organization(*, membership_id, caregiver_profile, reason=""):
    """Caregiver-owned: terminate one's own active membership.
    Ownership-authorized, never RBAC-gated."""
    membership = OrganizationMembership.objects.select_for_update().get(id=membership_id)
    if membership.user_id != caregiver_profile.user_id:
        raise AccountsError("This membership does not belong to this caregiver.")
    if membership.status != OrgMembershipStatus.ACTIVE:
        raise AccountsError("Only an active membership can be left.")

    _finalize_termination(
        membership, terminated_by=caregiver_profile.user, reason=reason or "Left by caregiver.",
    )
    return membership


def _finalize_termination(membership, *, terminated_by, reason) -> None:
    membership.status = OrgMembershipStatus.REMOVED
    membership.terminated_at = timezone.now()
    membership.terminated_by = terminated_by
    membership.termination_reason = reason
    membership.save(update_fields=["status", "terminated_at", "terminated_by", "termination_reason", "updated_at"])

    caregiver = CaregiverProfile.objects.filter(user=membership.user).first()
    if caregiver and caregiver.provider_type == CaregiverProviderType.ORGANIZATION_AFFILIATED:
        # Single-active-company policy (module docstring): reverting to
        # INDEPENDENT is always correct here, since this caregiver cannot
        # have had another active membership at the same time.
        caregiver.provider_type = CaregiverProviderType.INDEPENDENT
        caregiver.save(update_fields=["provider_type", "updated_at"])

    OrganizationRoleSyncService.sync_for_membership(membership)


# ============================================================
# Read helpers
# ============================================================


def list_pending_requests_for_organization(organization):
    return CompanyAffiliationRequest.objects.filter(
        organization=organization, status=AffiliationStatus.PENDING,
    ).select_related("caregiver_profile").order_by("-requested_at")


def list_pending_invitations_for_organization(organization):
    return OrganizationMembership.objects.filter(
        organization=organization, status=OrgMembershipStatus.PENDING, invited_by__isnull=False,
    ).select_related("user", "person").order_by("-created_at")


def list_membership_history_for_caregiver(caregiver_profile):
    return OrganizationMembership.objects.filter(
        user=caregiver_profile.user,
    ).select_related("organization").order_by("-updated_at")


def list_pending_invitations_for_caregiver(caregiver_profile):
    return OrganizationMembership.objects.filter(
        user=caregiver_profile.user, status=OrgMembershipStatus.PENDING, invited_by__isnull=False,
    ).select_related("organization").order_by("-created_at")


def list_affiliation_requests_for_caregiver(caregiver_profile):
    return CompanyAffiliationRequest.objects.filter(
        caregiver_profile=caregiver_profile,
    ).select_related("organization").order_by("-requested_at")


def get_active_membership_for_caregiver(caregiver_profile):
    return OrganizationMembership.objects.filter(
        user=caregiver_profile.user, status=OrgMembershipStatus.ACTIVE,
    ).select_related("organization").first()
