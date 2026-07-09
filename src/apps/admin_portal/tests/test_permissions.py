from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from apps.admin_portal.permission_keys import PORTAL_ACCESS
from apps.admin_portal.permissions import require_admin_permission, require_authenticated, resolve_tenant_id

from .helpers import AdminPortalTestCase


class RequireAuthenticatedTest(AdminPortalTestCase):
    def test_raises_for_anonymous_user(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            require_authenticated(request)

    def test_passes_for_authenticated_user(self):
        request = RequestFactory().get("/")
        request.user = self.actor

        require_authenticated(request)  # should not raise


class ResolveTenantIdTest(AdminPortalTestCase):
    def test_returns_users_own_tenant(self):
        request = RequestFactory().get("/")
        request.user = self.actor

        self.assertEqual(resolve_tenant_id(request), self.tenant.id)

    def test_raises_for_user_without_tenant(self):
        self.actor.tenant = None
        self.actor.save(update_fields=["tenant"])

        request = RequestFactory().get("/")
        request.user = self.actor

        with self.assertRaises(PermissionDenied):
            resolve_tenant_id(request)


class RequireAdminPermissionTest(AdminPortalTestCase):
    def test_denies_unauthenticated(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            require_admin_permission(request, PORTAL_ACCESS)

    def test_denies_authenticated_user_without_permission(self):
        request = RequestFactory().get("/")
        request.user = self.actor

        with self.assertRaises(PermissionDenied):
            require_admin_permission(request, PORTAL_ACCESS)

    def test_allows_authenticated_user_with_permission(self):
        self._grant(self.actor, self.tenant, [PORTAL_ACCESS])

        request = RequestFactory().get("/")
        request.user = self.actor

        tenant_id = require_admin_permission(request, PORTAL_ACCESS)
        self.assertEqual(tenant_id, self.tenant.id)

    def test_denies_when_permission_granted_in_a_different_tenant(self):
        self._grant(self.actor, self.other_tenant, [PORTAL_ACCESS])

        request = RequestFactory().get("/")
        request.user = self.actor

        with self.assertRaises(PermissionDenied):
            require_admin_permission(request, PORTAL_ACCESS)
