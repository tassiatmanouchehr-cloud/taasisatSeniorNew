"""End-to-end tests for DiscoveryService.search(): normalize + filter + rank + paginate."""

from apps.discovery.services import DiscoveryService

from .helpers import DiscoveryTestCase


class DiscoveryServiceTest(DiscoveryTestCase):
    def test_search_returns_page_with_total_count(self):
        for i in range(3):
            self._create_supplier(display_name=f"Supplier {i}")

        page = DiscoveryService.search(tenant_id=self.tenant.id)
        self.assertEqual(page.total_count, 3)
        self.assertEqual(len(page.items), 3)

    def test_search_respects_limit(self):
        for i in range(5):
            self._create_supplier(display_name=f"Supplier {i}")

        page = DiscoveryService.search(tenant_id=self.tenant.id, limit=2)
        self.assertEqual(page.total_count, 5)
        self.assertEqual(len(page.items), 2)
        self.assertEqual(page.limit, 2)

    def test_search_respects_offset(self):
        suppliers = [self._create_supplier(display_name=f"Supplier {i}") for i in range(5)]
        full_page = DiscoveryService.search(tenant_id=self.tenant.id, limit=10)

        offset_page = DiscoveryService.search(tenant_id=self.tenant.id, limit=10, offset=2)
        self.assertEqual(len(offset_page.items), 3)
        self.assertEqual(
            [item.supplier_id for item in offset_page.items],
            [item.supplier_id for item in full_page.items][2:],
        )

    def test_search_scopes_to_tenant(self):
        self._create_supplier(tenant=self.other_tenant)
        page = DiscoveryService.search(tenant_id=self.tenant.id)
        self.assertEqual(page.total_count, 0)

    def test_search_applies_category_filter(self):
        matching = self._create_supplier(service_categories=[str(self.category.id)])
        self._create_supplier(display_name="Other", service_categories=[str(self.other_category.id)])

        page = DiscoveryService.search(tenant_id=self.tenant.id, service_category_id=self.category.id)
        self.assertEqual(page.total_count, 1)
        self.assertEqual(page.items[0].supplier_id, matching.id)

    def test_search_with_no_results_returns_empty_page(self):
        page = DiscoveryService.search(tenant_id=self.tenant.id, text="nonexistent")
        self.assertEqual(page.total_count, 0)
        self.assertEqual(page.items, ())
