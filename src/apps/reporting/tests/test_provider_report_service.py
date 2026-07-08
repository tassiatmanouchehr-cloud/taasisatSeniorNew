from decimal import Decimal

from apps.kernel.models.supplier import AvailabilityStatus
from apps.reporting.dto import ProviderPerformanceReport
from apps.reporting.services import ProviderReportService

from .helpers import ReportingTestCase


class ProviderReportServiceTest(ReportingTestCase):
    def test_completed_services_and_reputation_reflect_the_fixture(self):
        report = ProviderReportService.get_report_for_supplier(self.tenant.id, self.supplier.id)

        self.assertEqual(report.completed_services, 1)
        self.assertEqual(report.reputation_review_count, 1)
        self.assertEqual(report.reputation_average, Decimal("4.50"))
        self.assertEqual(report.availability_status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(report.total_assignments, 1)
        # The assignment stays ASSIGNED even after the order completes (Booking never
        # auto-transitions it) — so it's still counted as "active" here.
        self.assertEqual(report.active_assignments, 1)

    def test_supplier_with_no_activity_returns_zeroed_report(self):
        other_supplier = self._create_supplier(tenant=self.tenant, display_name="Idle Supplier")

        report = ProviderReportService.get_report_for_supplier(self.tenant.id, other_supplier.id)

        self.assertEqual(report.completed_services, 0)
        self.assertEqual(report.reputation_review_count, 0)
        self.assertIsNone(report.reputation_average)
        self.assertEqual(report.total_assignments, 0)
        self.assertEqual(report.active_assignments, 0)

    def test_list_reports_covers_every_tenant_supplier(self):
        other_supplier = self._create_supplier(tenant=self.tenant, display_name="Second Supplier")

        reports = ProviderReportService.list_reports(self.tenant.id)

        supplier_ids = {r.supplier_id for r in reports}
        self.assertEqual(supplier_ids, {self.supplier.id, other_supplier.id})

    def test_tenant_isolation(self):
        other_supplier = self._create_supplier(tenant=self.other_tenant, display_name="Other Tenant Supplier")

        reports = ProviderReportService.list_reports(self.tenant.id)
        supplier_ids = {r.supplier_id for r in reports}
        self.assertNotIn(other_supplier.id, supplier_ids)

    def test_deterministic_output(self):
        first = ProviderReportService.get_report_for_supplier(self.tenant.id, self.supplier.id)
        second = ProviderReportService.get_report_for_supplier(self.tenant.id, self.supplier.id)
        self.assertEqual(first, second)

    def test_dto_is_immutable(self):
        report = ProviderReportService.get_report_for_supplier(self.tenant.id, self.supplier.id)
        with self.assertRaises(Exception):
            report.completed_services = 999

    def test_returns_dto_not_orm_objects(self):
        report = ProviderReportService.get_report_for_supplier(self.tenant.id, self.supplier.id)
        self.assertIsInstance(report, ProviderPerformanceReport)
