"""OrderQueryService.list_for_supplier()/count_by_status_for_supplier() —
Sprint 2.5 (Caregiver Professional Dashboard) work-summary selectors."""

import uuid

from django.test import TestCase

from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory
from apps.orders.services.queries import OrderQueryService
from apps.orders.services.status_machine import (
    approve_cancellation,
    assign_supplier,
    complete_order,
    request_cancellation,
    start_order,
)


class SupplierWorkSummaryQueryTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"orders-sup-{uuid.uuid4().hex[:8]}", name="Orders Supplier Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.supplier = self._create_supplier()
        self.other_supplier = self._create_supplier()

    def _create_supplier(self) -> ServiceSupplier:
        return ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile", display_name="Test Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC, service_categories=[],
        )

    def _create_order(self) -> Order:
        return Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="x", city="tehran", address="addr", phone="0912",
        )

    def test_no_orders_returns_zero_counts(self):
        counts = OrderQueryService.count_by_status_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id)
        self.assertEqual(counts, {"current": 0, "upcoming": 0, "completed": 0, "cancelled": 0})

    def test_upcoming_order_counted_and_listed(self):
        order = self._create_order()
        assign_supplier(order_id=order.id, supplier=self.supplier)

        counts = OrderQueryService.count_by_status_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id)
        self.assertEqual(counts["upcoming"], 1)
        upcoming = list(OrderQueryService.list_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id, only="upcoming"))
        self.assertEqual([o.id for o in upcoming], [order.id])

    def test_current_order_counted_and_listed(self):
        order = self._create_order()
        assign_supplier(order_id=order.id, supplier=self.supplier)
        start_order(order_id=order.id)

        counts = OrderQueryService.count_by_status_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id)
        self.assertEqual(counts["current"], 1)
        self.assertEqual(counts["upcoming"], 0)
        current = list(OrderQueryService.list_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id, only="current"))
        self.assertEqual([o.id for o in current], [order.id])

    def test_completed_order_counted_and_listed(self):
        order = self._create_order()
        assign_supplier(order_id=order.id, supplier=self.supplier)
        start_order(order_id=order.id)
        complete_order(order_id=order.id)

        counts = OrderQueryService.count_by_status_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id)
        self.assertEqual(counts["completed"], 1)
        completed = list(
            OrderQueryService.list_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id, only="completed"),
        )
        self.assertEqual([o.id for o in completed], [order.id])

    def test_cancelled_order_counted_and_listed(self):
        order = self._create_order()
        assign_supplier(order_id=order.id, supplier=self.supplier)
        request_cancellation(order_id=order.id, requested_by=None, reason="test")
        approve_cancellation(order_id=order.id)

        counts = OrderQueryService.count_by_status_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id)
        self.assertEqual(counts["cancelled"], 1)
        cancelled = list(
            OrderQueryService.list_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id, only="cancelled"),
        )
        self.assertEqual([o.id for o in cancelled], [order.id])

    def test_another_suppliers_orders_never_counted_or_listed(self):
        order = self._create_order()
        assign_supplier(order_id=order.id, supplier=self.other_supplier)

        counts = OrderQueryService.count_by_status_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id)
        self.assertEqual(counts["upcoming"], 0)
        listed = list(OrderQueryService.list_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id))
        self.assertEqual(listed, [])

    def test_limit_bounds_result_set(self):
        for _ in range(3):
            order = self._create_order()
            assign_supplier(order_id=order.id, supplier=self.supplier)

        limited = list(
            OrderQueryService.list_for_supplier(supplier=self.supplier, tenant_id=self.tenant.id, limit=2),
        )
        self.assertEqual(len(limited), 2)

    def test_cross_tenant_orders_never_leak(self):
        other_tenant = Tenant.objects.create(slug=f"orders-sup-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        other_category = ServiceCategory.objects.create(
            tenant=other_tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        other_supplier_same_id_space = ServiceSupplier.objects.create(
            tenant_id=other_tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile", display_name="Other Tenant Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC, service_categories=[],
        )
        other_order = Order.objects.create(
            tenant=other_tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=other_category, description="x", city="tehran", address="addr", phone="0912",
        )
        assign_supplier(order_id=other_order.id, supplier=other_supplier_same_id_space)

        listed = list(
            OrderQueryService.list_for_supplier(supplier=other_supplier_same_id_space, tenant_id=self.tenant.id),
        )
        self.assertEqual(listed, [])
