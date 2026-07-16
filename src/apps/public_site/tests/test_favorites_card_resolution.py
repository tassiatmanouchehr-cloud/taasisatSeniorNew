"""CaregiverDirectoryService/OrganizationDirectoryService
.build_cards_for_supplier_ids() — Phase 4 Sprint 4.1 (Customer Favorites
and Saved Providers).

Decision C/D (Sprint 4.1 ADR): these are purely additive classmethods
reusing each directory service's own existing bulk-resolution machinery
— covers explicit-id-set resolution, silent omission of no-longer-public
suppliers (never a KeyError/None entry the caller has to special-case),
and KL-012 query-budget stability at 0/1/5/20 candidate ids."""

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.kernel.models.supplier import SupplierStatus
from apps.public_site.services.directory_service import CaregiverDirectoryService
from apps.public_site.services.organization_directory_service import OrganizationDirectoryService

from .helpers import PublicSiteTestCase


class CaregiverBuildCardsForSupplierIdsTest(PublicSiteTestCase):
    def test_resolves_requested_suppliers(self):
        supplier, _ = self._create_caregiver_supplier(display_name="مراقب یک")
        other_supplier, _ = self._create_caregiver_supplier(display_name="مراقب دو")

        cards = CaregiverDirectoryService.build_cards_for_supplier_ids(
            [supplier.id, other_supplier.id], tenant_id=self.tenant.id,
        )

        self.assertEqual(set(cards.keys()), {supplier.id, other_supplier.id})
        self.assertEqual(cards[supplier.id].display_name, "مراقب یک")

    def test_empty_id_list_returns_empty_dict_with_no_query(self):
        with CaptureQueriesContext(connection) as ctx:
            cards = CaregiverDirectoryService.build_cards_for_supplier_ids([], tenant_id=self.tenant.id)
        self.assertEqual(cards, {})
        self.assertEqual(len(ctx.captured_queries), 0)

    def test_suspended_supplier_is_silently_omitted(self):
        supplier, _ = self._create_caregiver_supplier(
            display_name="غیرفعال", supplier_status=SupplierStatus.SUSPENDED,
        )
        cards = CaregiverDirectoryService.build_cards_for_supplier_ids([supplier.id], tenant_id=self.tenant.id)
        self.assertEqual(cards, {})

    def test_wrong_tenant_supplier_is_silently_omitted(self):
        from apps.kernel.models import Tenant
        import uuid

        other_tenant = Tenant.objects.create(slug=f"cg-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        old_tenant = self.tenant
        self.tenant = other_tenant
        cross_supplier, _ = self._create_caregiver_supplier(display_name="بین مستاجر")
        self.tenant = old_tenant

        cards = CaregiverDirectoryService.build_cards_for_supplier_ids(
            [cross_supplier.id], tenant_id=self.tenant.id,
        )
        self.assertEqual(cards, {})

    def test_query_count_bounded_at_representative_sizes(self):
        def count_for(n):
            supplier_ids = []
            for i in range(n):
                supplier, _ = self._create_caregiver_supplier(display_name=f"مراقب {i}")
                supplier_ids.append(supplier.id)
            with CaptureQueriesContext(connection) as ctx:
                CaregiverDirectoryService.build_cards_for_supplier_ids(supplier_ids, tenant_id=self.tenant.id)
            return len(ctx.captured_queries)

        count_at_1 = count_for(1)
        count_at_20 = count_for(20)
        self.assertLessEqual(count_at_20 - count_at_1, 6)


class OrganizationBuildCardsForSupplierIdsTest(PublicSiteTestCase):
    def test_resolves_requested_suppliers(self):
        supplier, _ = self._create_organization_supplier(name="سازمان یک")
        other_supplier, _ = self._create_organization_supplier(name="سازمان دو")

        cards = OrganizationDirectoryService.build_cards_for_supplier_ids(
            [supplier.id, other_supplier.id], tenant_id=self.tenant.id,
        )

        self.assertEqual(set(cards.keys()), {supplier.id, other_supplier.id})
        self.assertEqual(cards[supplier.id].name, "سازمان یک")

    def test_empty_id_list_returns_empty_dict_with_no_query(self):
        with CaptureQueriesContext(connection) as ctx:
            cards = OrganizationDirectoryService.build_cards_for_supplier_ids([], tenant_id=self.tenant.id)
        self.assertEqual(cards, {})
        self.assertEqual(len(ctx.captured_queries), 0)

    def test_query_count_bounded_at_representative_sizes(self):
        def count_for(n):
            supplier_ids = []
            for i in range(n):
                supplier, _ = self._create_organization_supplier(name=f"سازمان {i}")
                supplier_ids.append(supplier.id)
            with CaptureQueriesContext(connection) as ctx:
                OrganizationDirectoryService.build_cards_for_supplier_ids(supplier_ids, tenant_id=self.tenant.id)
            return len(ctx.captured_queries)

        count_at_1 = count_for(1)
        count_at_20 = count_for(20)
        self.assertLessEqual(count_at_20 - count_at_1, 6)
