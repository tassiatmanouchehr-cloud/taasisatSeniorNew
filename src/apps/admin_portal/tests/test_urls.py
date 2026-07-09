from django.test import TestCase
from django.urls import reverse


class AdminPortalUrlTest(TestCase):
    def test_routes_resolve_under_admin_portal_prefix(self):
        self.assertEqual(reverse("admin_portal:home"), "/admin-portal/")
        self.assertEqual(reverse("admin_portal:tenant-overview"), "/admin-portal/tenants/")
        self.assertEqual(reverse("admin_portal:supplier-overview"), "/admin-portal/suppliers/")
        self.assertEqual(reverse("admin_portal:order-overview"), "/admin-portal/orders/")
        self.assertEqual(reverse("admin_portal:finance-overview"), "/admin-portal/finance/")
        self.assertEqual(reverse("admin_portal:system-status"), "/admin-portal/system/")

    def test_does_not_conflict_with_django_admin(self):
        # /admin/ still resolves to Django's own admin site, not admin_portal.
        response = self.client.get("/admin/", follow=False)
        # Django admin login redirect or 200 — either way, NOT admin_portal's 403/200 shape.
        self.assertIn(response.status_code, (200, 302))

        # /admin-portal/ is a distinct prefix — unauthenticated here is a 403, not a Django-admin redirect.
        response = self.client.get("/admin-portal/")
        self.assertEqual(response.status_code, 403)

    def test_admin_portal_not_exposed_under_api_v1(self):
        response = self.client.get("/api/v1/admin-portal/")
        self.assertEqual(response.status_code, 404)
