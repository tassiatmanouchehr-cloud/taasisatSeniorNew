from apps.reporting.services import ReportingService

from .helpers import ReportingTestCase


class ReportingServiceTest(ReportingTestCase):
    def test_facade_delegates_to_order_counts(self):
        report = ReportingService.get_order_counts(self.tenant.id)
        self.assertEqual(report.total_orders, 1)

    def test_facade_delegates_to_provider_report(self):
        report = ReportingService.get_provider_report(self.tenant.id, self.supplier.id)
        self.assertEqual(report.supplier_id, self.supplier.id)

    def test_facade_delegates_to_list_provider_reports(self):
        reports = ReportingService.list_provider_reports(self.tenant.id)
        self.assertEqual(len(reports), 1)

    def test_facade_delegates_to_financial_summary(self):
        report = ReportingService.get_financial_summary(self.tenant.id)
        self.assertEqual(report.invoices_issued_count, 1)

    def test_facade_delegates_to_marketplace_stats(self):
        report = ReportingService.get_marketplace_stats(self.tenant.id)
        self.assertEqual(report.supplier_count, 1)
