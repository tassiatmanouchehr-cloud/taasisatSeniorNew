"""Tests for SupplierAssignment tenant isolation."""

from apps.booking.models import SupplierAssignment
from apps.booking.services.assignment_service import AssignmentService

from .helpers import BookingTestCase


class SupplierAssignmentTenantIsolationTest(BookingTestCase):
    def test_for_tenant_scopes_supplier_assignments(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)

        self.assertEqual(SupplierAssignment.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(SupplierAssignment.objects.for_tenant(self.other_tenant.id).count(), 0)

    def test_supplier_assignment_tenant_matches_order_tenant(self):
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        self.assertEqual(assignment.tenant_id, self.order.tenant_id)
