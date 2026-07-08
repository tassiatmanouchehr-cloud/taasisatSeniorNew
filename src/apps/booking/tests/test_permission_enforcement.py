"""
Tests proving AssignmentService.assign() denies an unauthorized actor and
produces zero business-side effects (no Order mutation, no SupplierAssignment row).
"""

from apps.booking.models import SupplierAssignment
from apps.booking.services.assignment_service import AssignmentService
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.orders.models import OrderStatus

from .helpers import BookingTestCase


class AssignmentPermissionEnforcementTest(BookingTestCase):
    def setUp(self):
        super().setUp()
        self.unauthorized_actor = make_actor(self.tenant, full_name="No Permission Actor")
        self.supplier = self._create_supplier()

    def test_assign_denied_without_permission(self):
        with self.assertRaises(PermissionDenied):
            AssignmentService.assign(
                order_id=self.order.id, supplier=self.supplier, assigned_by=self.unauthorized_actor,
            )

        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 0)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)
        self.assertIsNone(self.order.assigned_supplier_id)

    def test_assign_allowed_with_permission(self):
        grant_permissions(self.tenant, self.unauthorized_actor, ["booking.assignment.assign"])

        assignment = AssignmentService.assign(
            order_id=self.order.id, supplier=self.supplier, assigned_by=self.unauthorized_actor,
        )

        self.assertIsNotNone(assignment.pk)
        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, self.supplier.id)

    def test_assign_still_works_with_no_actor_supplied(self):
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
        self.assertIsNotNone(assignment.pk)
