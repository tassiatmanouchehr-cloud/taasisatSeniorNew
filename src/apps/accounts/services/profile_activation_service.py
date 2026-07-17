"""ProfileActivationService — Phase 1.3 (Profile Activation and
Completion), corrected in the Phase 1.3 remediation (PR #5).

The explicit, authorized, audited action that performs the real
DRAFT -> ACTIVE profile-status transition for a caregiver's/
organization's profile.

Root defect fixed in this remediation: the original Phase 1.3
implementation treated `AuditLog` existence as the activation source of
truth ("activation is true because a matching AuditLog exists") and never
actually changed `profile.status`, because profiles already defaulted to
`ProfileStatus.ACTIVE` at registration. That made "activation" a no-op
recording action with no real state transition behind it.

`profile.status` is now the sole source of truth for a profile's current
activation state — `ProfileStatus.DRAFT` (registered, not yet
platform-activated; the new default at registration —
`RegistrationService.create_caregiver()`/`create_company_admin()`),
`ProfileStatus.ACTIVE` (explicitly activated), `ProfileStatus.SUSPENDED`
(administratively blocked). `AuditLog` is written on every real
transition as permanent historical evidence of *when* and *by whom* the
transition happened — it is consulted for nothing else. In particular,
`is_activated()` below reads `profile.status` directly and never queries
`AuditLog`.

Never activates automatically — nothing calls this except an explicit,
authorized request. Never suspends/deactivates an already-active profile
— that is an explicitly deferred, distinct revalidation/suspension
workflow (see `project docs/quality/COMPLETION_BACKLOG.md` BG-019).

Idempotency is now derived from `profile.status` itself: if the locked
profile is already `ACTIVE`, `activate_*()` returns immediately with
`transitioned=False` — no eligibility re-check (an already-active profile
must not be re-blocked by, say, a document that expired after it was
activated — that is the same deferred deactivation concern) and no
second "effective" `AuditLog` entry.

Core Profile-ServiceSupplier Invariant Remediation: a real DRAFT -> ACTIVE
transition also synchronously guarantees, in this same transaction, that
the profile's ServiceSupplier exists and is itself ACTIVE (via
`supplier_bridge.sync_supplier_for_profile_activation()`) — this is now
the sole code path that establishes that invariant. `ProfileActivationService`
remains the sole owner of `DRAFT -> ACTIVE`; it is not a general profile-
lifecycle facade — suspension/reactivation/archival remain out of scope
(deferred, see `project docs/quality/COMPLETION_BACKLOG.md` BG-019).
"""

from dataclasses import dataclass

from django.db import transaction

from apps.kernel.permissions.keys import ACCOUNTS_PROFILE_ACTIVATE
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from .activation_eligibility_service import ActivationEligibilityResult, ActivationEligibilityService
from .errors import AccountsError
from .supplier_bridge import sync_supplier_for_profile_activation

MODULE_ID = "M08"
ACTIVATION_AUDIT_ACTION = "accounts.profile.activated"


class ProfileActivationError(AccountsError):
    """Raised when activation is refused — a controlled domain error
    carrying the exact `ActivationEligibilityResult` reasons, never a
    bare exception. Covers both "DRAFT but ineligible" and "SUSPENDED/
    ARCHIVED" refusals, since both are reported as blocking reasons by
    `ActivationEligibilityService`."""

    def __init__(self, result: ActivationEligibilityResult):
        self.result = result
        super().__init__(f"Profile is not eligible for activation: {', '.join(result.reasons)}")


@dataclass(frozen=True)
class ProfileActivationResult:
    """The structured outcome of one `activate_*()` call.

    `transitioned` is True only when this call actually performed the
    DRAFT -> ACTIVE state change and wrote the corresponding `AuditLog`
    entry. A repeated call against an already-`ACTIVE` profile returns
    `transitioned=False` (idempotent no-op: no duplicate state
    transition, no duplicate effective audit entry)."""

    profile: object
    previous_status: str
    status: str
    transitioned: bool


class ProfileActivationService:
    @classmethod
    @transaction.atomic
    def activate_caregiver(cls, caregiver_id, *, tenant_id, actor) -> ProfileActivationResult:
        try:
            locked = CaregiverProfile.objects.select_for_update().get(id=caregiver_id)
        except CaregiverProfile.DoesNotExist:
            raise AccountsError("Profile not found.") from None

        if locked.user.tenant_id != tenant_id:
            raise AccountsError("Profile not found.")

        PermissionService.require(actor, ACCOUNTS_PROFILE_ACTIVATE, tenant_id=tenant_id)

        if actor is not None and getattr(actor, "id", None) == locked.user_id:
            raise AccountsError("A profile owner cannot activate their own profile.")

        return cls._activate(locked, resource_type="CaregiverProfile", tenant_id=tenant_id, actor=actor)

    @classmethod
    @transaction.atomic
    def activate_organization(cls, organization_id, *, tenant_id, actor) -> ProfileActivationResult:
        try:
            locked = OrganizationProfile.objects.select_for_update().get(id=organization_id)
        except OrganizationProfile.DoesNotExist:
            raise AccountsError("Profile not found.") from None

        if locked.tenant_id != tenant_id:
            raise AccountsError("Profile not found.")

        PermissionService.require(actor, ACCOUNTS_PROFILE_ACTIVATE, tenant_id=tenant_id)

        if actor is not None and getattr(actor, "id", None) == locked.admin_user_id:
            raise AccountsError("A profile owner cannot activate their own profile.")

        return cls._activate(locked, resource_type="OrganizationProfile", tenant_id=tenant_id, actor=actor)

    @classmethod
    def get_caregiver_for_tenant(cls, *, caregiver_id, tenant_id) -> CaregiverProfile:
        """Non-locking, read-only lookup for GET views — `activate_caregiver()`
        performs its own row-locked lookup separately; a GET request must
        never take a lock."""
        try:
            caregiver = CaregiverProfile.objects.select_related("user").get(id=caregiver_id)
        except CaregiverProfile.DoesNotExist:
            raise AccountsError("Profile not found.") from None
        if caregiver.user.tenant_id != tenant_id:
            raise AccountsError("Profile not found.")
        return caregiver

    @classmethod
    def get_organization_for_tenant(cls, *, organization_id, tenant_id) -> OrganizationProfile:
        try:
            organization = OrganizationProfile.objects.select_related("admin_user").get(id=organization_id)
        except OrganizationProfile.DoesNotExist:
            raise AccountsError("Profile not found.") from None
        if organization.tenant_id != tenant_id:
            raise AccountsError("Profile not found.")
        return organization

    @staticmethod
    def is_activated(profile) -> bool:
        """`profile.status` is the sole source of truth for current
        activation state. `AuditLog` is historical evidence of the
        transition only and is never consulted here."""
        return profile.status == ProfileStatus.ACTIVE

    @classmethod
    def _activate(cls, profile, *, resource_type: str, tenant_id, actor) -> ProfileActivationResult:
        previous_status = profile.status

        if profile.status == ProfileStatus.ACTIVE:
            return ProfileActivationResult(
                profile=profile, previous_status=previous_status, status=profile.status, transitioned=False,
            )

        result = ActivationEligibilityService.evaluate(profile)
        if not result.eligible:
            raise ProfileActivationError(result)

        profile.status = ProfileStatus.ACTIVE
        profile.save(update_fields=["status", "updated_at"])

        # Core Profile-ServiceSupplier Invariant Remediation: activation must
        # synchronously guarantee ServiceSupplier existence + ACTIVE status in
        # this same transaction. Uncaught on failure by design — the
        # surrounding @transaction.atomic (activate_caregiver/
        # activate_organization) then rolls back the profile transition above
        # together with any partial supplier change and the audit record
        # below, which is written only after this succeeds.
        sync_supplier_for_profile_activation(profile, tenant_id=tenant_id)

        AuditService.log(
            tenant_id=tenant_id,
            action=ACTIVATION_AUDIT_ACTION,
            resource_type=resource_type,
            resource_id=profile.id,
            module_id=MODULE_ID,
            actor_id=getattr(actor, "person_id", None),
            actor_type="user" if actor else "system",
            before={"status": previous_status},
            after={"status": profile.status, "verification_status": result.verification.verification_status},
        )
        return ProfileActivationResult(
            profile=profile, previous_status=previous_status, status=profile.status, transitioned=True,
        )
