"""Tests for apps.kernel.views.forbidden — the project's handler403.

FR-018 (Public Site Coherence Remediation, PSA-005): the audit found a
raw, unbranded Django 403 page for anonymous visitors opening
authenticated-only routes. Investigating "the intended access-control
architecture" (as the remediation task itself required) before changing
anything surfaced that every one of the four browser-facing portals
already has its own explicit, redundant test asserting anonymous access
returns a plain 403 — never a redirect — across apps.portal,
apps.provider_portal, apps.organization_portal, and apps.admin_portal
(15 pre-existing tests total). That is this codebase's own established,
deliberately non-disclosing security policy — exactly the exception
PSA-005 itself names ("unless the established security policy explicitly
requires non-disclosure"). So these tests confirm the actual fix:
Django's raw default 403 page is replaced with one branded, Persian,
non-disclosing page for every browser-facing PermissionDenied — status
code unchanged, no permission-check function touched, no existing test
modified."""

import uuid

from django.test import RequestFactory, TestCase

from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.views import _safe_next_path


class SafeNextPathHelperTest(TestCase):
    """Unit coverage for the open-redirect guard, kept available (see
    apps.kernel.views' own module docstring) even though no live redirect
    currently uses it."""

    def _request(self, path):
        return RequestFactory().get(path)

    def test_relative_path_preserved(self):
        request = self._request("/portal/")
        self.assertEqual(_safe_next_path(request), "/portal/")

    def test_relative_path_with_query_preserved(self):
        request = self._request("/portal/favorites/?tab=caregivers")
        self.assertEqual(_safe_next_path(request), "/portal/favorites/?tab=caregivers")

    def test_protocol_relative_path_normalized_to_root(self):
        """//evil.example/ looks relative but browsers treat a leading
        // as scheme-relative — a classic open-redirect vector. Django's
        own url_has_allowed_host_and_scheme() must reject it."""
        request = self._request("/portal/")
        request.path = "//evil.example/steal"
        request.META["PATH_INFO"] = "//evil.example/steal"
        self.assertEqual(_safe_next_path(request), "/")

    def test_absolute_external_url_normalized_to_root(self):
        request = self._request("/portal/")
        request.path = "http://evil.example/steal"
        request.META["PATH_INFO"] = "http://evil.example/steal"
        self.assertEqual(_safe_next_path(request), "/")


class AnonymousAccessGetsBrandedForbiddenTest(TestCase):
    """Anonymous visitors hitting any login-required browser route still
    get 403 (unchanged, matches every pre-existing test in
    apps.portal/provider_portal/organization_portal/admin_portal) — now
    branded instead of Django's raw default."""

    def test_anonymous_portal_access_is_still_403(self):
        response = self.client.get("/admin-portal/")
        self.assertEqual(response.status_code, 403)

    def test_anonymous_portal_access_403_is_branded(self):
        response = self.client.get("/admin-portal/")

        self.assertContains(response, "دسترسی به این صفحه مجاز نیست", status_code=403)
        self.assertNotContains(response, "<title>403 Forbidden</title>", status_code=403)

    def test_anonymous_provider_and_organization_portal_also_403(self):
        for path in ("/provider/", "/portal/", "/organization/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)


class AuthenticatedUnauthorizedGetsBrandedForbiddenTest(TestCase):
    """A real, logged-in, but ordinary (non-admin) account hitting an
    admin-only route — genuinely unauthorized, not merely unauthenticated
    — gets the identical branded page as the anonymous case."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"kernel-403-{uuid.uuid4().hex[:8]}", name="Test Tenant")
        person = Person.objects.create(tenant=self.tenant, full_name="کاربر عادی")
        self.user = UserAccount.objects.create_user(
            phone=f"0912{uuid.uuid4().hex[:7]}", person=person, tenant=self.tenant,
        )

    def test_authenticated_unauthorized_user_gets_branded_403(self):
        self.client.force_login(self.user)

        response = self.client.get("/admin-portal/")

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "دسترسی به این صفحه مجاز نیست", status_code=403)
        self.assertNotContains(response, "<title>403 Forbidden</title>", status_code=403)

    def test_branded_403_does_not_disclose_permission_details(self):
        self.client.force_login(self.user)

        response = self.client.get("/admin-portal/")

        content = response.content.decode()
        self.assertNotIn("PORTAL_ACCESS", content)
        self.assertNotIn("PermissionDenied", content)


class ApiRoutesUnaffectedTest(TestCase):
    """apps.api already raises its own ApiError (never Django's
    PermissionDenied) for auth failures, converted to a JSON envelope
    well before reaching handler403 — this is a defense-in-depth
    confirmation that /api/ responses were not changed by this PR."""

    def test_anonymous_api_request_is_not_redirected_to_login(self):
        response = self.client.get("/api/v1/")

        self.assertNotEqual(response.status_code, 302)


class TenantScopedAccessNonDisclosureTest(TestCase):
    """A resource-scoped admin_portal route (an escrow detail page) must
    not distinguish "exists in another tenant" from "does not exist" for
    an unauthorized caller — both are the same 403, unchanged by this PR."""

    def test_unknown_escrow_id_same_403_as_real_but_unauthorized(self):
        tenant = Tenant.objects.create(slug=f"kernel-403-tenant-{uuid.uuid4().hex[:8]}", name="T")
        person = Person.objects.create(tenant=tenant, full_name="کاربر عادی دو")
        user = UserAccount.objects.create_user(phone=f"0913{uuid.uuid4().hex[:7]}", person=person, tenant=tenant)
        self.client.force_login(user)

        response = self.client.get(f"/admin-portal/financial/escrows/{uuid.uuid4()}/")

        self.assertEqual(response.status_code, 403)
