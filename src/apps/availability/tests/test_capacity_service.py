"""
Tests for CapacityService: concurrent-engagement counting and capacity-
exceeded evaluation, for both an independent-provider supplier and an
organization-type supplier.
"""

from apps.booking.services.assignment_service import AssignmentService
from apps.kernel.models.supplier import SupplierType
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory

from ..services import CapacityService
from .helpers import AvailabilityTestCase


class CapacityServiceTest(AvailabilityTestCase):
    def setUp(self):
        super().setUp()
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )

    def _make_order(self):
        return Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            description="Need home care",
            city="tehran",
            address="Some address",
            phone="09120000000",
        )

    def test_no_rule_means_not_exceeded(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self._make_order().id, supplier=supplier)

        self.assertFalse(CapacityService.is_capacity_exceeded(supplier=supplier))

    def test_capacity_not_exceeded_below_max(self):
        supplier = self._create_supplier()
        CapacityService.set_capacity_rule(supplier=supplier, max_concurrent_assignments=2)
        AssignmentService.assign(order_id=self._make_order().id, supplier=supplier)

        self.assertEqual(CapacityService.get_active_engagement_count(supplier=supplier), 1)
        self.assertFalse(CapacityService.is_capacity_exceeded(supplier=supplier))

    def test_capacity_exceeded_at_max(self):
        supplier = self._create_supplier()
        CapacityService.set_capacity_rule(supplier=supplier, max_concurrent_assignments=1)
        AssignmentService.assign(order_id=self._make_order().id, supplier=supplier)

        self.assertTrue(CapacityService.is_capacity_exceeded(supplier=supplier))

    def test_inactive_capacity_rule_is_ignored(self):
        supplier = self._create_supplier()
        CapacityService.set_capacity_rule(supplier=supplier, max_concurrent_assignments=1, is_active=False)
        AssignmentService.assign(order_id=self._make_order().id, supplier=supplier)

        self.assertFalse(CapacityService.is_capacity_exceeded(supplier=supplier))

    def test_set_capacity_rule_is_idempotent_per_supplier(self):
        supplier = self._create_supplier()
        CapacityService.set_capacity_rule(supplier=supplier, max_concurrent_assignments=2)
        rule = CapacityService.set_capacity_rule(supplier=supplier, max_concurrent_assignments=5)

        from ..models import CapacityRule

        self.assertEqual(CapacityRule.objects.filter(supplier=supplier).count(), 1)
        self.assertEqual(rule.max_concurrent_assignments, 5)

    def test_organization_supplier_capacity_works_identically(self):
        org_supplier = self._create_supplier(supplier_type=SupplierType.ORGANIZATION, display_name="Care Org")
        CapacityService.set_capacity_rule(supplier=org_supplier, max_concurrent_assignments=3)

        AssignmentService.assign(order_id=self._make_order().id, supplier=org_supplier)
        AssignmentService.assign(order_id=self._make_order().id, supplier=org_supplier)

        self.assertEqual(CapacityService.get_active_engagement_count(supplier=org_supplier), 2)
        self.assertFalse(CapacityService.is_capacity_exceeded(supplier=org_supplier))

        AssignmentService.assign(order_id=self._make_order().id, supplier=org_supplier)
        self.assertTrue(CapacityService.is_capacity_exceeded(supplier=org_supplier))
