from apps.orders.models import OrderShareLink
from apps.orders.services.order_creation import create_public_order

from .helpers import PortalTestCase


class ShareLinkViewsTest(PortalTestCase):
    def setUp(self):
        super().setUp()
        self.order = create_public_order(
            service_category_id=self.category.id, description="x", phone="09120000000",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
        )

    def test_create_share_link(self):
        self.login_as_customer()
        response = self.client.post(f"/portal/requests/{self.order.id}/share/")
        self.assertRedirects(response, f"/portal/requests/{self.order.id}/")
        self.assertTrue(OrderShareLink.objects.filter(order=self.order).exists())

    def test_cannot_create_share_link_for_another_customers_order(self):
        self.client.force_login(self.other_customer.user)
        response = self.client.post(f"/portal/requests/{self.order.id}/share/")
        self.assertEqual(response.status_code, 404)

    def test_revoke_share_link(self):
        self.login_as_customer()
        self.client.post(f"/portal/requests/{self.order.id}/share/")
        link = OrderShareLink.objects.get(order=self.order)
        response = self.client.post(f"/portal/requests/{self.order.id}/share/{link.id}/revoke/")
        self.assertRedirects(response, f"/portal/requests/{self.order.id}/")
        link.refresh_from_db()
        self.assertIsNotNone(link.revoked_at)


class SharedOrderPublicViewTest(PortalTestCase):
    def setUp(self):
        super().setUp()
        self.order = create_public_order(
            service_category_id=self.category.id, description="x", phone="09120000000",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
        )

    def test_shared_order_view_requires_no_login(self):
        from apps.orders.services.share_links import OrderShareLinkService

        link = OrderShareLinkService.create(order=self.order)
        response = self.client.get(f"/portal/share/{link.token}/")
        self.assertEqual(response.status_code, 200)

    def test_shared_order_view_rejects_unknown_token(self):
        response = self.client.get("/portal/share/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_shared_order_view_does_not_expose_dashboard_or_wallet_links(self):
        from apps.orders.services.share_links import OrderShareLinkService

        link = OrderShareLinkService.create(order=self.order)
        response = self.client.get(f"/portal/share/{link.token}/")
        self.assertNotContains(response, "/portal/notifications/")
        self.assertNotContains(response, 'href="/portal/"')
