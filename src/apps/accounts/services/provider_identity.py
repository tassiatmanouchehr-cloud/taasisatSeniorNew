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
"""

from apps.kernel.models.supplier import ServiceSupplier

from .errors import AccountsError
from .supplier_bridge import get_or_create_supplier_for_caregiver


def resolve_supplier_for_user(user) -> ServiceSupplier:
    """Returns the ServiceSupplier for the given UserAccount's own provider
    profile. Raises AccountsError if the account has no provider profile —
    never guesses, never accepts a supplier id from a caller."""
    caregiver = getattr(user, "caregiver_profile", None)
    if caregiver is None:
        raise AccountsError("This account has no provider profile.")
    return get_or_create_supplier_for_caregiver(caregiver, tenant_id=user.tenant_id)
