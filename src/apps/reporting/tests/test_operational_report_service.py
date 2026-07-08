from apps.orders.models import Order, OrderSource, OrderStatus
from apps.reporting.dto import OrderCountsReport
from apps.reporting.services import OperationalReportService

from .helpers import ReportingTestCase


class OperationalReportServiceTest(ReportingTestCase):
    def test_order_counts_reflect_the_completed_fixture_order(self):
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.COMPLETED)

        report = OperationalReportService.get_order_counts(self.tenant.id)

        self.assertEqual(report.total_orders, 1)
        self.assertEqual(report.completed_orders, 1)
        self.assertEqual(report.cancelled_orders, 0)
        self.assertEqual(report.active_orders, 0)
        self.assertEqual(report.by_status, {OrderStatus.COMPLETED: 1})

    def test_order_counts_with_additional_active_and_cancelled_orders(self):
        Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, customer_profile=self.customer_profile,
            description="x", city="tehran", address="addr", phone="09120000001",
        )
        Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.CANCELLED,
            service_category=self.category, customer_profile=self.customer_profile,
            description="x", city="tehran", address="addr", phone="09120000002",
        )
        Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.IN_PROGRESS,
            service_category=self.category, customer_profile=self.customer_profile,
            description="x", city="tehran", address="addr", phone="09120000003",
        )

        report = OperationalReportService.get_order_counts(self.tenant.id)

        self.assertEqual(report.total_orders, 4)
        self.assertEqual(report.completed_orders, 1)
        self.assertEqual(report.cancelled_orders, 1)
        self.assertEqual(report.active_orders, 2)

    def test_empty_dataset_returns_zeroed_report(self):
        report = OperationalReportService.get_order_counts(self.other_tenant.id)

        self.assertEqual(report.total_orders, 0)
        self.assertEqual(report.active_orders, 0)
        self.assertEqual(report.completed_orders, 0)
        self.assertEqual(report.cancelled_orders, 0)
        self.assertEqual(report.by_status, {})

    def test_tenant_isolation(self):
        Order.objects.create(
            tenant=self.other_tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, customer_profile=self.customer_profile,
            description="x", city="tehran", address="addr", phone="09120000004",
        )

        report = OperationalReportService.get_order_counts(self.tenant.id)
        self.assertEqual(report.total_orders, 1)

        other_report = OperationalReportService.get_order_counts(self.other_tenant.id)
        self.assertEqual(other_report.total_orders, 1)

    def test_deterministic_output(self):
        first = OperationalReportService.get_order_counts(self.tenant.id)
        second = OperationalReportService.get_order_counts(self.tenant.id)

        self.assertEqual(first, second)

    def test_dto_is_immutable(self):
        report = OperationalReportService.get_order_counts(self.tenant.id)

        with self.assertRaises(Exception):
            report.total_orders = 999

    def test_returns_dto_not_orm_objects(self):
        report = OperationalReportService.get_order_counts(self.tenant.id)
        self.assertIsInstance(report, OrderCountsReport)
        self.assertNotIsInstance(report, Order)
