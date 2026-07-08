from apps.api.permission_keys import DISCOVERY_SUPPLIERS_READ

from .helpers import ApiTestCase


class DiscoveryEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/v1/discovery/suppliers/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_without_permission_is_forbidden(self):
        self.client.force_login(self.actor)
        response = self.client.get("/api/v1/discovery/suppliers/")
        self.assertEqual(response.status_code, 403)

    def test_lists_active_suppliers_in_own_tenant(self):
        self._grant(self.actor, self.tenant, [DISCOVERY_SUPPLIERS_READ])
        self.client.force_login(self.actor)

        response = self.client.get("/api/v1/discovery/suppliers/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["supplier_id"], str(self.supplier.id))

    def test_filters_by_supplier_type(self):
        self._grant(self.actor, self.tenant, [DISCOVERY_SUPPLIERS_READ])
        self.client.force_login(self.actor)

        from apps.kernel.models.supplier import SupplierType
        self._create_supplier(tenant=self.tenant, supplier_type=SupplierType.ORGANIZATION, display_name="Org Supplier")

        response = self.client.get("/api/v1/discovery/suppliers/?supplier_type=ORGANIZATION")

        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["display_name"], "Org Supplier")

    def test_pagination_is_applied(self):
        self._grant(self.actor, self.tenant, [DISCOVERY_SUPPLIERS_READ])
        self.client.force_login(self.actor)

        self._create_supplier(tenant=self.tenant, display_name="Second Supplier")

        response = self.client.get("/api/v1/discovery/suppliers/?limit=1&offset=0")

        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["limit"], 1)
        self.assertEqual(body["total_count"], 2)
        self.assertTrue(body["has_more"])

    def test_does_not_leak_other_tenants_suppliers(self):
        self._grant(self.actor, self.tenant, [DISCOVERY_SUPPLIERS_READ])
        self.client.force_login(self.actor)
        self._create_supplier(tenant=self.other_tenant, display_name="Other Tenant Supplier")

        response = self.client.get("/api/v1/discovery/suppliers/")

        supplier_ids = {item["supplier_id"] for item in response.json()["results"]}
        self.assertNotIn(str(self.other_tenant.id), supplier_ids)
        self.assertEqual(len(response.json()["results"]), 1)
