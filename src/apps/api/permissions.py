"""
API auth/RBAC utility hooks — Module 17A foundation.

Reuses the existing session-auth (request.user is a real kernel.UserAccount
once logged in) and apps.kernel.services.permission_service.PermissionService
— no second authentication or authorization system is introduced here.
"""

import uuid

from apps.kernel.services.permission_service import PermissionService

from .errors import ApiError


def require_authenticated(request) -> None:
    """Raises ApiError(401) unless request.user is a real, authenticated UserAccount."""
    if not getattr(request.user, "is_authenticated", False):
        raise ApiError(code="authentication_required", message="Authentication is required.", status_code=401)


def resolve_tenant_id(request) -> uuid.UUID:
    """Returns the authenticated user's own tenant_id. Call require_authenticated() first."""
    tenant_id = getattr(request.user, "tenant_id", None)
    if not tenant_id:
        raise ApiError(
            code="tenant_required",
            message="The authenticated account has no tenant context.",
            status_code=400,
        )
    return tenant_id


def require_permission(request, permission_key: str, *, scope: dict | None = None) -> uuid.UUID:
    """Authenticates, resolves tenant_id, and enforces the RBAC permission_key. Returns tenant_id.

    Raises ApiError(401)/ApiError(400), or lets PermissionDenied propagate to
    ApiView's exception mapping (-> 403) on RBAC failure.
    """
    require_authenticated(request)
    tenant_id = resolve_tenant_id(request)
    PermissionService.require(request.user, permission_key, tenant_id=tenant_id, scope=scope)
    return tenant_id
