"""
Customer portal auth utility hooks — Customer Experience Phase 1.

Mirrors apps.admin_portal.permissions (Module 19), which itself mirrors
apps.api.permissions (Module 17A/17B): reuses the existing session-auth
(request.user is a real kernel.UserAccount once logged in) — no second
authentication system. Unlike admin_portal, the customer portal has no
RBAC permission keys to check: a customer is always allowed to see their
own data, and never anyone else's. The one check that matters is
ownership — resolve_customer_profile() below, mirroring
apps.api.permissions.resolve_customer_profile() (not imported directly:
apps.api sits at the top of the dependency graph and nothing may import
it — see docs/architecture/dependency-graph.md).
"""

import uuid

from django.core.exceptions import PermissionDenied


def require_authenticated(request) -> None:
    """Raises PermissionDenied (-> 403) unless request.user is a real, authenticated UserAccount."""
    if not getattr(request.user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required to access the customer portal.")


def resolve_tenant_id(request) -> uuid.UUID:
    """Returns the authenticated user's own tenant_id. Call require_authenticated() first.
    CustomerProfile itself has no tenant field — UserAccount is the source of truth."""
    tenant_id = getattr(request.user, "tenant_id", None)
    if not tenant_id:
        raise PermissionDenied("The authenticated account has no tenant context.")
    return tenant_id


def resolve_customer_profile(request):
    """Returns the authenticated user's own CustomerProfile. Never accepted from the
    request body/URL — prevents one customer from acting as another. Call
    require_authenticated() first."""
    from apps.accounts.models.profiles import CustomerProfile

    person = getattr(request.user, "person", None)
    if person is None:
        raise PermissionDenied("The authenticated account has no associated customer profile.")

    try:
        return person.customer_profile
    except CustomerProfile.DoesNotExist:
        raise PermissionDenied("The authenticated account has no associated customer profile.")
