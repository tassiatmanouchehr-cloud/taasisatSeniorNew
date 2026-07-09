"""Every /portal/ page requires authentication and only ever shows the caller's own data."""

from .helpers import PortalTestCase

PAGES = (
    "/portal/",
    "/portal/care-recipients/",
    "/portal/care-recipients/new/",
    "/portal/requests/",
    "/portal/notifications/",
    "/portal/requests/new/care-recipient/",
)


class UnauthenticatedAccessTest(PortalTestCase):
    def test_every_page_denies_anonymous_users(self):
        for path in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)


class AuthenticatedAccessTest(PortalTestCase):
    def test_every_page_is_reachable_once_logged_in(self):
        self.login_as_customer()
        for path in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_care_recipient_edit_denies_other_customers_recipient(self):
        self.login_as_customer()
        self.client.logout()
        self.client.force_login(self.other_customer.user)
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_request_detail_denies_other_customers_order(self):
        from apps.orders.services.order_creation import create_public_order

        self.login_as_customer()
        order = create_public_order(
            service_category_id=self.category.id, description="x", phone="09120000000",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
        )
        self.client.logout()
        self.client.force_login(self.other_customer.user)
        response = self.client.get(f"/portal/requests/{order.id}/")
        self.assertEqual(response.status_code, 404)
