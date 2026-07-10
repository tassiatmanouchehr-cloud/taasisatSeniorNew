"""
Provider portal auth utility hooks — Epic 02 (Marketplace Operational
Experience).

Mirrors apps.portal.permissions exactly in shape: session auth (no second
authentication system), ownership as the security boundary (a provider is
always allowed to see their own assignments/visits/availability/earnings,
never anyone else's), no RBAC permission keys. resolve_supplier() is the
one call site that turns a UserAccount into the generic
kernel.ServiceSupplier this entire app operates on — see
apps.accounts.services.provider_identity for why the portal itself never
imports CaregiverProfile (or any future individual-supplier profile type):
this app is supplier-generic by construction, reusable later for nurses,
physiotherapists, technicians, etc. without any change here.
"""

import uuid

from django.core.exceptions import PermissionDenied


def require_authenticated(request) -> None:
    """Raises PermissionDenied (-> 403) unless request.user is a real, authenticated UserAccount."""
    if not getattr(request.user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required to access the provider portal.")


def resolve_tenant_id(request) -> uuid.UUID:
    tenant_id = getattr(request.user, "tenant_id", None)
    if not tenant_id:
        raise PermissionDenied("The authenticated account has no tenant context.")
    return tenant_id


def resolve_supplier(request):
    """Returns the authenticated user's own ServiceSupplier. Never accepted
    from the request body/URL — prevents one provider from acting as
    another. Call require_authenticated() first."""
    from apps.accounts.services.errors import AccountsError
    from apps.accounts.services.provider_identity import resolve_supplier_for_user

    try:
        return resolve_supplier_for_user(request.user)
    except AccountsError:
        raise PermissionDenied("The authenticated account has no provider profile.")
