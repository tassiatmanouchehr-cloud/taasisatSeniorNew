"""Tests for candidate generation (via SupplierResolver) and tenant isolation."""

from apps.kernel.models.supplier import AvailabilityStatus
from apps.kernel.services.supplier_resolver import SupplierResolver

from .helpers import MatchingTestCase


class CandidateGenerationTest(MatchingTestCase):
    def _generate(self):
        return list(
            SupplierResolver.get_suppliers_for_matching(
                tenant_id=self.tenant.id, service_category_id=self.category.id,
            )
        )

    def test_generates_matching_category_supplier(self):
        supplier = self._create_supplier()
        self.assertIn(supplier, self._generate())

    def test_excludes_supplier_of_other_category(self):
        supplier = self._create_supplier(service_categories=[str(self.other_category.id)])
        self.assertNotIn(supplier, self._generate())

    def test_cross_tenant_supplier_never_appears(self):
        other_supplier = self._create_supplier(tenant=self.other_tenant)
        candidates = self._generate()
        self.assertNotIn(other_supplier, candidates)
        for candidate in candidates:
            self.assertEqual(candidate.tenant_id, self.tenant.id)

    def test_offline_supplier_excluded_from_generation(self):
        supplier = self._create_supplier(availability_status=AvailabilityStatus.OFFLINE)
        self.assertNotIn(supplier, self._generate())

    def test_generation_only_returns_requested_tenant(self):
        same_category_other_tenant = self._create_supplier(
            tenant=self.other_tenant, service_categories=[str(self.category.id)],
        )
        matching_supplier = self._create_supplier()
        candidates = self._generate()
        self.assertIn(matching_supplier, candidates)
        self.assertNotIn(same_category_other_tenant, candidates)
