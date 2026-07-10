"""
Organization portal auth utility hooks — Epic 02 (Marketplace Operational
Experience).

Mirrors apps.portal.permissions exactly in shape: session auth, ownership
as the security boundary, no RBAC permission keys. resolve_organization()
never accepts an organization id from the request — it always resolves
"the organization I administer" via
apps.accounts.services.organization_identity.list_administered_organizations,
the same "resolve the caller's own identity, never accept one from the
request" pattern every other portal in this codebase uses.

Deliberately scoped to exactly one organization per admin for this phase
— an admin who somehow administers more than one sees only the first
(by creation order). Multi-organization switching is explicitly deferred
(see DECISION_HISTORY.md); nothing about this resolver blocks adding it
later, since every view already calls resolve_organization() exactly
once and never hardcodes an organization id.
"""

import uuid

from django.core.exceptions import PermissionDenied


def require_authenticated(request) -> None:
    """Raises PermissionDenied (-> 403) unless request.user is a real, authenticated UserAccount."""
    if not getattr(request.user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required to access the organization portal.")


def resolve_tenant_id(request) -> uuid.UUID:
    tenant_id = getattr(request.user, "tenant_id", None)
    if not tenant_id:
        raise PermissionDenied("The authenticated account has no tenant context.")
    return tenant_id


def resolve_organization(request):
    """Returns the authenticated user's own (first) administered
    OrganizationProfile. Call require_authenticated() first."""
    from apps.accounts.services.organization_identity import list_administered_organizations

    organization = list_administered_organizations(request.user).first()
    if organization is None:
        raise PermissionDenied("The authenticated account does not administer any organization.")
    return organization
