"""
Admin portal auth/RBAC utility hooks — Module 19.

Mirrors apps.api.permissions (Module 17A/17B) but for plain server-rendered
Django views instead of DRF: reuses the existing session-auth (request.user
is a real kernel.UserAccount once logged in) and
apps.kernel.services.permission_service.PermissionService directly — no
second authentication or authorization system, no admin-portal-specific
login flow. Denial raises Django's own django.core.exceptions
.PermissionDenied, which Django's default exception handling turns into a
403 response automatically (no custom exception handler needed here,
unlike the DRF-based apps.api layer).
"""

import uuid

from django.core.exceptions import PermissionDenied

from apps.kernel.services.permission_service import PermissionService


def require_authenticated(request) -> None:
    """Raises PermissionDenied (-> 403) unless request.user is a real, authenticated UserAccount."""
    if not getattr(request.user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required to access the admin portal.")


def resolve_tenant_id(request) -> uuid.UUID:
    """Returns the authenticated user's own tenant_id. Call require_authenticated() first."""
    tenant_id = getattr(request.user, "tenant_id", None)
    if not tenant_id:
        raise PermissionDenied("The authenticated account has no tenant context.")
    return tenant_id


def require_admin_permission(request, permission_key: str) -> uuid.UUID:
    """Authenticates, resolves tenant_id, and enforces the RBAC permission_key. Returns tenant_id.

    Raises PermissionDenied (-> 403) on any failure — no authentication,
    no tenant, or RBAC denial (apps.kernel.services.errors.PermissionDenied
    from PermissionService.require() is allowed to propagate too; Django
    maps any PermissionDenied subclass-or-not exception name collision
    aside, only its own django.core.exceptions.PermissionDenied is
    special-cased by the framework, so we translate explicitly below).
    """
    require_authenticated(request)
    tenant_id = resolve_tenant_id(request)

    from apps.kernel.services.errors import PermissionDenied as RbacPermissionDenied

    try:
        PermissionService.require(request.user, permission_key, tenant_id=tenant_id)
    except RbacPermissionDenied as exc:
        raise PermissionDenied(str(exc)) from exc

    return tenant_id
