"""Every /provider/ page requires authentication and only ever shows the caller's own data."""

from .helpers import ProviderPortalTestCase

PAGES = (
    "/provider/",
    "/provider/assignments/",
    "/provider/availability/",
    "/provider/earnings/",
    "/provider/notifications/",
)


class UnauthenticatedAccessTest(ProviderPortalTestCase):
    def test_every_page_denies_anonymous_users(self):
        for path in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)


class NonProviderAccountAccessTest(ProviderPortalTestCase):
    def test_customer_without_provider_profile_is_denied(self):
        self.client.force_login(self.customer.user)
        response = self.client.get("/provider/")
        self.assertEqual(response.status_code, 403)


class AuthenticatedAccessTest(ProviderPortalTestCase):
    def test_every_page_is_reachable_once_logged_in(self):
        self.login_as_provider()
        for path in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_assignment_detail_denies_other_providers_assignment(self):
        self.assign_order_to_supplier()
        self.client.force_login(self.other_provider_user)
        response = self.client.get(f"/provider/assignments/{self.order.id}/")
        self.assertEqual(response.status_code, 404)

    def test_assignment_detail_denies_cross_tenant_order(self):
        """self.provider_user (tenant A) requesting an order that belongs to
        a wholly different tenant B, assigned to a tenant-B supplier —
        must 404, not leak the other tenant's assignment."""
        self.assign_cross_tenant_order_to_supplier()
        self.login_as_provider()
        response = self.client.get(f"/provider/assignments/{self.other_tenant_order.id}/")
        self.assertEqual(response.status_code, 404)

    def test_assignments_list_never_contains_cross_tenant_order(self):
        self.assign_order_to_supplier()
        self.assign_cross_tenant_order_to_supplier()
        self.login_as_provider()
        response = self.client.get("/provider/assignments/")
        self.assertContains(response, self.order.order_number)
        self.assertNotContains(response, self.other_tenant_order.order_number)
