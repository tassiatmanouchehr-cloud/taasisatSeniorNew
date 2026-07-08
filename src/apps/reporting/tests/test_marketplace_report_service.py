from apps.accounts.models.profiles import OrganizationProfile
from apps.kernel.models.supplier import SupplierType
from apps.reporting.dto import MarketplaceStatsReport
from apps.reporting.services import MarketplaceReportService

from .helpers import ReportingTestCase


class MarketplaceReportServiceTest(ReportingTestCase):
    def test_marketplace_stats_reflect_the_fixture(self):
        report = MarketplaceReportService.get_marketplace_stats(self.tenant.id)

        self.assertEqual(report.supplier_count, 1)
        self.assertEqual(report.customer_count, 1)
        self.assertEqual(report.organization_count, 0)
        self.assertEqual(report.supplier_type_distribution, {SupplierType.INDEPENDENT_PROVIDER: 1})
        self.assertEqual(report.category_distribution, {self.category.name: 1})

    def test_organization_count_is_tenant_scoped(self):
        OrganizationProfile.objects.create(
            name="Org A", code=f"org-{self.tenant.id.hex[:8]}", admin_user=self.customer_profile.user,
            tenant=self.tenant,
        )
        OrganizationProfile.objects.create(
            name="Org B", code=f"org-other-{self.other_tenant.id.hex[:8]}", admin_user=self.customer_profile.user,
            tenant=self.other_tenant,
        )

        report = MarketplaceReportService.get_marketplace_stats(self.tenant.id)
        self.assertEqual(report.organization_count, 1)

    def test_supplier_type_distribution_covers_multiple_types(self):
        self._create_supplier(
            tenant=self.tenant, supplier_type=SupplierType.ORGANIZATION, display_name="Org Supplier",
        )

        report = MarketplaceReportService.get_marketplace_stats(self.tenant.id)

        self.assertEqual(report.supplier_count, 2)
        self.assertEqual(
            report.supplier_type_distribution,
            {SupplierType.INDEPENDENT_PROVIDER: 1, SupplierType.ORGANIZATION: 1},
        )

    def test_empty_dataset_returns_zeroed_report(self):
        report = MarketplaceReportService.get_marketplace_stats(self.other_tenant.id)

        self.assertEqual(report.supplier_count, 0)
        self.assertEqual(report.organization_count, 0)
        self.assertEqual(report.customer_count, 0)
        self.assertEqual(report.supplier_type_distribution, {})
        self.assertEqual(report.category_distribution, {})

    def test_tenant_isolation(self):
        self._create_supplier(tenant=self.other_tenant, display_name="Other Tenant Supplier")

        report = MarketplaceReportService.get_marketplace_stats(self.tenant.id)
        self.assertEqual(report.supplier_count, 1)

    def test_deterministic_output(self):
        first = MarketplaceReportService.get_marketplace_stats(self.tenant.id)
        second = MarketplaceReportService.get_marketplace_stats(self.tenant.id)
        self.assertEqual(first, second)

    def test_dto_is_immutable(self):
        report = MarketplaceReportService.get_marketplace_stats(self.tenant.id)
        with self.assertRaises(Exception):
            report.supplier_count = 999

    def test_returns_dto_not_orm_objects(self):
        report = MarketplaceReportService.get_marketplace_stats(self.tenant.id)
        self.assertIsInstance(report, MarketplaceStatsReport)
