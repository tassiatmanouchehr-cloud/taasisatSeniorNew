from django.test import TestCase


class HealthEndpointTest(TestCase):
    def test_health_endpoint_is_unauthenticated_and_healthy(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["db"], "ok")
        self.assertEqual(data["cache"], "ok")

    def test_health_endpoint_includes_correlation_id(self):
        response = self.client.get("/api/v1/health/", HTTP_X_CORRELATION_ID="test-correlation-123")

        self.assertEqual(response.json()["correlation_id"], "test-correlation-123")
        self.assertEqual(response["X-Correlation-ID"], "test-correlation-123")
