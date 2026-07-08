from .helpers import ApiTestCase


class OrderCountsSampleEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/v1/sample/order-counts/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_required")

    def test_authenticated_without_permission_is_forbidden(self):
        self.client.force_login(self.actor)

        response = self.client.get("/api/v1/sample/order-counts/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "permission_denied")

    def test_authenticated_with_permission_returns_report(self):
        self._grant(self.actor, self.tenant, ["reporting.read"])
        self.client.force_login(self.actor)

        response = self.client.get("/api/v1/sample/order-counts/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_orders"], 1)
        self.assertEqual(body["tenant_id"], str(self.tenant.id))

    def test_report_is_scoped_to_the_actors_own_tenant(self):
        self._grant(self.actor, self.tenant, ["reporting.read"])
        self.client.force_login(self.actor)

        other_customer = self._create_customer(tenant=self.other_tenant, display_name="Other")
        from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        Order.objects.create(
            tenant=self.other_tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=other_category, customer_profile=other_customer,
            description="x", city="tehran", address="addr", phone="09120000099",
        )

        response = self.client.get("/api/v1/sample/order-counts/")
        self.assertEqual(response.json()["total_orders"], 1)


class ProviderReportsSampleEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/v1/sample/providers/")
        self.assertEqual(response.status_code, 401)

    def test_returns_paginated_results(self):
        self._grant(self.actor, self.tenant, ["reporting.read"])
        self._create_supplier(tenant=self.tenant, display_name="Second Supplier")
        self.client.force_login(self.actor)

        response = self.client.get("/api/v1/sample/providers/?limit=1&offset=0")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["limit"], 1)
        self.assertEqual(body["total_count"], 2)
        self.assertTrue(body["has_more"])

    def test_invalid_pagination_param_returns_validation_error(self):
        self._grant(self.actor, self.tenant, ["reporting.read"])
        self.client.force_login(self.actor)

        response = self.client.get("/api/v1/sample/providers/?limit=not-a-number")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_result_items_are_json_serializable_dtos(self):
        self._grant(self.actor, self.tenant, ["reporting.read"])
        self.client.force_login(self.actor)

        response = self.client.get("/api/v1/sample/providers/")

        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["supplier_id"], str(self.supplier.id))
