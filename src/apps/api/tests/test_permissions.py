from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.api.errors import ApiError
from apps.kernel.services.errors import PermissionDenied

from .helpers import ApiTestCase
from apps.api.permissions import require_authenticated, require_permission, resolve_tenant_id


class RequireAuthenticatedTest(ApiTestCase):
    def test_raises_for_anonymous_user(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        with self.assertRaises(ApiError) as ctx:
            require_authenticated(request)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_passes_for_authenticated_user(self):
        request = RequestFactory().get("/")
        request.user = self.actor

        require_authenticated(request)  # should not raise


class ResolveTenantIdTest(ApiTestCase):
    def test_returns_users_own_tenant(self):
        request = RequestFactory().get("/")
        request.user = self.actor

        self.assertEqual(resolve_tenant_id(request), self.tenant.id)

    def test_raises_for_user_without_tenant(self):
        superuser = self.actor
        superuser.tenant = None
        superuser.save(update_fields=["tenant"])

        request = RequestFactory().get("/")
        request.user = superuser

        with self.assertRaises(ApiError) as ctx:
            resolve_tenant_id(request)
        self.assertEqual(ctx.exception.status_code, 400)


class RequirePermissionTest(ApiTestCase):
    def test_denies_unauthenticated(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        with self.assertRaises(ApiError) as ctx:
            require_permission(request, "reporting.read")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_denies_authenticated_user_without_permission(self):
        request = RequestFactory().get("/")
        request.user = self.actor

        with self.assertRaises(PermissionDenied):
            require_permission(request, "reporting.read")

    def test_allows_authenticated_user_with_permission(self):
        self._grant(self.actor, self.tenant, ["reporting.read"])

        request = RequestFactory().get("/")
        request.user = self.actor

        tenant_id = require_permission(request, "reporting.read")
        self.assertEqual(tenant_id, self.tenant.id)

    def test_denies_when_permission_granted_in_a_different_tenant(self):
        self._grant(self.actor, self.other_tenant, ["reporting.read"])

        request = RequestFactory().get("/")
        request.user = self.actor

        with self.assertRaises(PermissionDenied):
            require_permission(request, "reporting.read")
