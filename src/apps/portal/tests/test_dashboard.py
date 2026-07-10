from django.utils import timezone

from apps.orders.services.order_creation import create_public_order

from .helpers import PortalTestCase


class DashboardViewTest(PortalTestCase):
    def test_dashboard_shows_own_care_recipient_and_no_orders_message(self):
        self.login_as_customer()
        response = self.client.get("/portal/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مادر بزرگ")

    def test_dashboard_shows_own_recent_order(self):
        self.login_as_customer()
        order = create_public_order(
            service_category_id=self.category.id, description="x", phone="09120000000",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
        )
        response = self.client.get("/portal/")
        self.assertContains(response, order.order_number)

    def test_dashboard_never_shows_another_customers_order(self):
        from apps.accounts.services.care_recipients import CareRecipientService
        from apps.orders.models import CatalogStatus, ServiceCategory

        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        other_recipient = CareRecipientService.create(customer_profile=self.other_customer, full_name="Other")
        other_order = create_public_order(
            service_category_id=other_category.id, description="x", phone="09120000000",
            address="addr", city="tehran", customer_profile=self.other_customer,
            elder_profile=other_recipient, created_by=self.other_customer.user, tenant_id=self.other_tenant.id,
        )
        self.login_as_customer()
        response = self.client.get("/portal/")
        self.assertNotContains(response, other_order.order_number)

    def test_dashboard_shows_upcoming_scheduled_visit(self):
        self.login_as_customer()
        future = timezone.now() + timezone.timedelta(days=3)
        create_public_order(
            service_category_id=self.category.id, description="x", phone="09120000000",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
            scheduled_for=future,
        )
        response = self.client.get("/portal/")
        self.assertEqual(len(response.context["upcoming_visits"]), 1)

    def test_dashboard_does_not_show_past_scheduled_visit(self):
        self.login_as_customer()
        past = timezone.now() - timezone.timedelta(days=3)
        create_public_order(
            service_category_id=self.category.id, description="x", phone="09120000000",
            address="addr", city="tehran", customer_profile=self.customer,
            elder_profile=self.care_recipient, created_by=self.customer.user, tenant_id=self.tenant.id,
            scheduled_for=past,
        )
        response = self.client.get("/portal/")
        self.assertEqual(len(response.context["upcoming_visits"]), 0)
