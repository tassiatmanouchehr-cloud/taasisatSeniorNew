"""
Base API view — Module 17A foundation.

DRF's own dispatch() -> handle_exception() -> settings.REST_FRAMEWORK
["EXCEPTION_HANDLER"] (apps.api.exception_handler.api_exception_handler)
maps exceptions to the standard error envelope. permission_classes =
[AllowAny] on every view is deliberate: apps.api.permissions functions
perform the real auth/tenant/RBAC enforcement manually (reusing
PermissionService), not DRF's own permission framework.
"""

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class ApiView(APIView):
    """Base class for all apps.api views."""

    permission_classes = [AllowAny]
