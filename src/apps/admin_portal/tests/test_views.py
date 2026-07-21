from apps.admin_portal.permission_keys import (
    FINANCE_READ,
    ORDERS_READ,
    PORTAL_ACCESS,
    SUPPLIERS_READ,
    SYSTEM_READ,
    TENANTS_READ,
)
from apps.orders.models import Order

from .helpers import AdminPortalTestCase

PAGES = (
    ("/admin-portal/", PORTAL_ACCESS),
    ("/admin-portal/tenants/", TENANTS_READ),
    ("/admin-portal/suppliers/", SUPPLIERS_READ),
    ("/admin-portal/orders/", ORDERS_READ),
    ("/admin-portal/finance/", FINANCE_READ),
    ("/admin-portal/system/", SYSTEM_READ),
)


class AdminPortalAccessControlTest(AdminPortalTestCase):
    def test_unauthenticated_users_are_denied_every_page(self):
        for path, _key in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)

    def test_non_admin_authenticated_users_are_denied_every_page(self):
        self.client.force_login(self.actor)
        for path, _key in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)

    def test_authorized_user_can_access_each_page(self):
        for path, key in PAGES:
            self._grant(self.actor, self.tenant, [key])
            self.client.force_login(self.actor)
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_permission_for_one_page_does_not_grant_another(self):
        self._grant(self.actor, self.tenant, [PORTAL_ACCESS])
        self.client.force_login(self.actor)

        response = self.client.get("/admin-portal/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/admin-portal/finance/")
        self.assertEqual(response.status_code, 403)


class AdminPortalTenantIsolationTest(AdminPortalTestCase):
    def test_order_overview_only_reflects_own_tenant(self):
        self._grant(self.actor, self.tenant, [ORDERS_READ])
        self.client.force_login(self.actor)

        from apps.orders.models import CatalogStatus, OrderSource, OrderStatus, ServiceCategory

        other_customer = self._create_customer(tenant=self.other_tenant, display_name="Other")
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        Order.objects.create(
            tenant=self.other_tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=other_category,
            customer_profile=other_customer,
            description="x",
            city="tehran",
            address="addr",
            phone="09120000099",
        )

        response = self.client.get("/admin-portal/orders/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1")  # this tenant has exactly 1 order

    def test_supplier_overview_only_reflects_own_tenant(self):
        self._grant(self.actor, self.tenant, [SUPPLIERS_READ])
        self.client.force_login(self.actor)

        self._create_supplier(tenant=self.other_tenant, display_name="Other Tenant Supplier")

        response = self.client.get("/admin-portal/suppliers/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Other Tenant Supplier")


class AdminPortalReadOnlyTest(AdminPortalTestCase):
    def test_no_writes_performed_by_any_page(self):
        for _path, key in PAGES:
            self._grant(self.actor, self.tenant, [key])
        self.client.force_login(self.actor)

        order_count_before = Order.objects.count()
        supplier_count_before = self.tenant.service_suppliers.count()

        for path, _key in PAGES:
            self.client.get(path)

        self.assertEqual(Order.objects.count(), order_count_before)
        self.assertEqual(self.tenant.service_suppliers.count(), supplier_count_before)

    def test_pages_only_accept_get(self):
        self._grant(self.actor, self.tenant, [PORTAL_ACCESS])
        self.client.force_login(self.actor)

        response = self.client.post("/admin-portal/", {})
        self.assertEqual(response.status_code, 405)
