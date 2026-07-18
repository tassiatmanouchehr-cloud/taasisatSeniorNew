"""
Provider identity resolution — Epic 02 (Marketplace Operational Experience).

Resolves a logged-in UserAccount to the generic kernel.ServiceSupplier
that represents them in the marketplace. This is the one place that
knows *how* a UserAccount becomes a supplier today (via CaregiverProfile)
— every caller (apps.provider_portal, and any future consumer) only ever
sees a ServiceSupplier, exactly like apps.matching/apps.booking/
apps.execution/apps.discovery already do. Adding a new individual-supplier
profile type later (nurse, physiotherapist, technician, ...) means adding
a branch inside resolve_supplier_for_user() — the function's contract
(UserAccount in, ServiceSupplier out) does not change, so no caller needs
to change either.

Mirrors apps.accounts.services.supplier_bridge (the ServiceSupplier <->
profile translator this module builds on) and
apps.portal.permissions.resolve_customer_profile's shape (resolve the
caller's own identity, never accept one from the request).

Core Profile-ServiceSupplier Invariant Remediation: this module now
strictly separates two different needs its callers have always actually
had, previously conflated into one always-creating function:

- A caller that genuinely needs a real, working ServiceSupplier to act
  on (confirm/decline an assignment, start/complete a visit, read
  availability/earnings/capacity) must get one only for an ACTUALLY
  ACTIVE provider profile — `resolve_supplier_for_user()` now raises
  AccountsError for a non-ACTIVE profile instead of silently
  materializing an ACTIVE ServiceSupplier for a profile that was never
  platform-activated. This is not a regression for any of its current
  callers: a genuine SupplierAssignment/booking/execution action can only
  exist for a profile that was already ACTIVE when it was created, and
  `provider_portal.permissions.resolve_supplier()` already converts
  AccountsError into PermissionDenied.
- A caller that only needs to *render the caller's own identity* (a
  profile page, a dashboard, a settings form) — where a DRAFT/SUSPENDED/
  ARCHIVED profile must still be viewable — uses the new
  `resolve_provider_context_for_user()` instead, which never creates a
  supplier for a non-ACTIVE profile and returns `supplier=None` so the
  caller can render a not-yet-activated state.
"""

from dataclasses import dataclass

from apps.kernel.models.supplier import ServiceSupplier

from ..models.profiles import CaregiverProfile, ProfileStatus
from .errors import AccountsError
from .supplier_bridge import get_or_create_supplier_for_caregiver


@dataclass(frozen=True)
class ProviderIdentityContext:
    """The caller's own CaregiverProfile, plus their ServiceSupplier if
    (and only if) their profile has actually reached ACTIVE. `supplier`
    is None for a DRAFT/SUSPENDED/ARCHIVED profile — never a lazily
    created one, per the Profile-ServiceSupplier activation invariant."""

    caregiver: CaregiverProfile
    supplier: ServiceSupplier | None


def resolve_provider_context_for_user(user) -> ProviderIdentityContext:
    """Returns the caller's own CaregiverProfile and, only if it is
    ACTIVE, their ServiceSupplier (resolved/repaired through the
    sanctioned bridge — never created for a non-ACTIVE profile). Raises
    AccountsError only if the account has no provider profile at all —
    never for a DRAFT/SUSPENDED/ARCHIVED one; callers that need to render
    the caller's own not-yet-activated identity get `supplier=None`
    instead of a PermissionDenied."""
    caregiver = getattr(user, "caregiver_profile", None)
    if caregiver is None:
        raise AccountsError("This account has no provider profile.")
    if caregiver.status != ProfileStatus.ACTIVE:
        return ProviderIdentityContext(caregiver=caregiver, supplier=None)
    supplier = get_or_create_supplier_for_caregiver(caregiver, tenant_id=user.tenant_id)
    return ProviderIdentityContext(caregiver=caregiver, supplier=supplier)


def resolve_supplier_for_user(user) -> ServiceSupplier:
    """Returns the ServiceSupplier for the given UserAccount's own
    ACTIVE provider profile. Raises AccountsError if the account has no
    provider profile, or if that profile has never reached ACTIVE — a
    profile that has never reached ACTIVE must not obtain a
    ServiceSupplier through identity resolution. Never guesses, never
    accepts a supplier id from a caller. Callers that need to render the
    caller's own identity even while DRAFT (a profile/status page) should
    use `resolve_provider_context_for_user()` instead."""
    caregiver = getattr(user, "caregiver_profile", None)
    if caregiver is None:
        raise AccountsError("This account has no provider profile.")
    if caregiver.status != ProfileStatus.ACTIVE:
        raise AccountsError("This account's provider profile has not been activated yet.")
    return get_or_create_supplier_for_caregiver(caregiver, tenant_id=user.tenant_id)
