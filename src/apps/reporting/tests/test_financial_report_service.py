from decimal import Decimal

from apps.reporting.dto import FinancialSummaryReport
from apps.reporting.services import FinancialReportService

from .helpers import ReportingTestCase


class FinancialReportServiceTest(ReportingTestCase):
    def test_financial_summary_reflects_the_fixture(self):
        report = FinancialReportService.get_financial_summary(self.tenant.id)

        self.assertEqual(report.invoices_issued_count, 1)
        self.assertEqual(report.invoices_issued_total, self.document.total_amount)
        self.assertEqual(report.payments_succeeded_count, 1)
        self.assertEqual(report.payments_succeeded_total, self.document.total_amount)
        self.assertEqual(report.wallet_total_balance, Decimal("50000.00"))
        self.assertEqual(report.wallet_transaction_count, 1)
        self.assertEqual(report.wallet_transaction_total, Decimal("50000.00"))

    def test_empty_dataset_returns_zeroed_report(self):
        report = FinancialReportService.get_financial_summary(self.other_tenant.id)

        self.assertEqual(report.invoices_issued_count, 0)
        self.assertEqual(report.invoices_issued_total, Decimal("0"))
        self.assertEqual(report.payments_succeeded_count, 0)
        self.assertEqual(report.payments_succeeded_total, Decimal("0"))
        self.assertEqual(report.wallet_total_balance, Decimal("0"))
        self.assertEqual(report.wallet_transaction_count, 0)
        self.assertEqual(report.wallet_transaction_total, Decimal("0"))

    def test_tenant_isolation(self):
        report = FinancialReportService.get_financial_summary(self.tenant.id)
        other_report = FinancialReportService.get_financial_summary(self.other_tenant.id)

        self.assertEqual(report.invoices_issued_count, 1)
        self.assertEqual(other_report.invoices_issued_count, 0)

    def test_amounts_are_decimal(self):
        report = FinancialReportService.get_financial_summary(self.tenant.id)

        self.assertIsInstance(report.invoices_issued_total, Decimal)
        self.assertIsInstance(report.payments_succeeded_total, Decimal)
        self.assertIsInstance(report.wallet_total_balance, Decimal)
        self.assertIsInstance(report.wallet_transaction_total, Decimal)

    def test_deterministic_output(self):
        first = FinancialReportService.get_financial_summary(self.tenant.id)
        second = FinancialReportService.get_financial_summary(self.tenant.id)
        self.assertEqual(first, second)

    def test_dto_is_immutable(self):
        report = FinancialReportService.get_financial_summary(self.tenant.id)
        with self.assertRaises(Exception):
            report.invoices_issued_count = 999

    def test_returns_dto_not_orm_objects(self):
        report = FinancialReportService.get_financial_summary(self.tenant.id)
        self.assertIsInstance(report, FinancialSummaryReport)
