from django.test import TestCase
from django.urls import NoReverseMatch, reverse


class ApiUrlVersioningTest(TestCase):
    def test_api_v1_health_route_resolves(self):
        self.assertEqual(reverse("api-v1:health-check"), "/api/v1/health/")

    def test_api_v1_sample_routes_resolve(self):
        self.assertEqual(reverse("api-v1:sample-order-counts"), "/api/v1/sample/order-counts/")
        self.assertEqual(reverse("api-v1:sample-providers"), "/api/v1/sample/providers/")

    def test_no_unversioned_health_route_exists(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 404)

    def test_no_unversioned_sample_route_exists(self):
        response = self.client.get("/sample/order-counts/")
        self.assertEqual(response.status_code, 404)

    def test_legacy_kernel_api_namespace_is_no_longer_the_routing_entrypoint(self):
        with self.assertRaises(NoReverseMatch):
            reverse("kernel-api:health-check")

    def test_module_17b_routes_resolve_under_api_v1(self):
        self.assertEqual(reverse("api-v1:discovery-suppliers"), "/api/v1/discovery/suppliers/")
        self.assertEqual(reverse("api-v1:pricing-quotes-create"), "/api/v1/pricing/quotes/")
        self.assertEqual(reverse("api-v1:reviews-submit"), "/api/v1/reviews/")
        self.assertEqual(reverse("api-v1:wallet-balance"), "/api/v1/wallet/balance/")
        self.assertEqual(reverse("api-v1:wallet-transactions"), "/api/v1/wallet/transactions/")
        self.assertEqual(reverse("api-v1:payments-intents-create"), "/api/v1/payments/intents/")
        self.assertEqual(reverse("api-v1:payments-callbacks-fake"), "/api/v1/payments/callbacks/fake/")

    def test_no_unversioned_module_17b_routes_exist(self):
        for path in (
            "/discovery/suppliers/",
            "/pricing/quotes/",
            "/reviews/",
            "/wallet/balance/",
            "/payments/intents/",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, path)

    def test_no_reporting_write_endpoints_exposed(self):
        # Reporting stays read-only/GET-only — no POST/PUT/DELETE routes exist for it.
        response = self.client.post("/api/v1/sample/order-counts/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 405)
