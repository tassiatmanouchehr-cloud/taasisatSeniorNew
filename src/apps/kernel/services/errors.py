"""
Shared kernel service exceptions.

`PermissionDenied` here is the platform's RBAC-authorization-denial
exception — deliberately distinct from `django.core.exceptions.PermissionDenied`
(which is a framework-level HTTP 403 signal for views). Business modules
should catch/raise `apps.kernel.services.errors.PermissionDenied`, not
Django's, when reacting to an authorization decision from PermissionService.
"""


class PermissionDenied(Exception):
    """Raised by PermissionService when an actor is not authorized for a permission_key."""
