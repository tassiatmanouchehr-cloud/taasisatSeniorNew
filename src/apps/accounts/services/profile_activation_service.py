"""ProfileActivationService — Phase 1.3 (Profile Activation and
Completion).

The explicit, audited, platform-staff-gated action that formally records
a caregiver's/organization's profile as activated. Distinct from the
`ProfileStatus.ACTIVE` a profile's own `status` field already carries by
default at registration (unchanged, existing behavior — see
`RegistrationService.create_caregiver()`/`create_company_admin()`): most
profiles are already "active" in that narrower DB-field sense the moment
they are created. What did NOT exist before this phase was any explicit,
permission-gated, audited record of platform staff having reviewed and
approved a profile against the platform's activation bar
(`ActivationEligibilityService`, Phase 1.2, itself unchanged by this
module) — that record is what this service adds.

Never activates automatically — nothing calls this except an explicit,
authorized request. Never suspends/deactivates an already-active profile
— that is an explicitly deferred, distinct revalidation/suspension
workflow (see `project docs/quality/COMPLETION_BACKLOG.md`).

Idempotency without a new field: the presence of an
"accounts.profile.activated" `AuditLog` entry for this exact
(tenant, resource_type, resource_id) is the sole signal that a profile
has already been activated — reusing `AuditLog` as the natural
idempotency key, the same "look up before create" shape
`apps.commission`'s `idempotency_key`-based services already use
elsewhere in this codebase, rather than adding a new field to track
"has this profile been activated."
"""

from django.db import transaction

from apps.kernel.permissions.keys import ACCOUNTS_PROFILE_ACTIVATE
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from .activation_eligibility_service import ActivationEligibilityResult, ActivationEligibilityService
from .errors import AccountsError

MODULE_ID = "M08"
ACTIVATION_AUDIT_ACTION = "accounts.profile.activated"


class ProfileActivationError(AccountsError):
    """Raised when activation is refused — a controlled domain error
    carrying the exact `ActivationEligibilityResult` reasons, never a
    bare exception."""

    def __init__(self, result: ActivationEligibilityResult):
        self.result = result
        super().__init__(f"Profile is not eligible for activation: {', '.join(result.reasons)}")


class ProfileActivationService:
    @classmethod
    @transaction.atomic
    def activate_caregiver(cls, caregiver_id, *, tenant_id, actor):
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
    def activate_organization(cls, organization_id, *, tenant_id, actor):
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

    @classmethod
    def is_activated(cls, *, resource_type: str, resource_id, tenant_id) -> bool:
        """Read-only — used by both `_activate()`'s idempotency guard and
        presentation services (`ProviderProfilePresentationService`/
        `OrganizationProfilePresentationService`) that need to show the
        owner their current activation state without duplicating this
        lookup."""
        from apps.kernel.models.audit import AuditLog

        return AuditLog.objects.filter(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=ACTIVATION_AUDIT_ACTION,
        ).exists()

    @classmethod
    def _activate(cls, profile, *, resource_type: str, tenant_id, actor):
        if cls.is_activated(resource_type=resource_type, resource_id=profile.id, tenant_id=tenant_id):
            return profile  # idempotent no-op — already formally activated

        result = ActivationEligibilityService.evaluate(profile)
        if not result.eligible:
            raise ProfileActivationError(result)

        if profile.status != ProfileStatus.ACTIVE:
            profile.status = ProfileStatus.ACTIVE
            profile.save(update_fields=["status", "updated_at"])

        AuditService.log(
            tenant_id=tenant_id,
            action=ACTIVATION_AUDIT_ACTION,
            resource_type=resource_type,
            resource_id=profile.id,
            module_id=MODULE_ID,
            actor_id=getattr(actor, "person_id", None),
            actor_type="user" if actor else "system",
            after={"status": profile.status, "verification_status": result.verification.verification_status},
        )
        return profile
