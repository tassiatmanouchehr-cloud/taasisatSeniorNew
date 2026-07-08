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
