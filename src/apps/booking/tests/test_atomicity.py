"""
Tests proving AssignmentService methods are wrapped in transaction.atomic():
a failure anywhere inside assign()/replace()/cancel() must roll back
EVERYTHING — both the orders.status_machine mutation and the
SupplierAssignment row — not leave partial state behind.
"""

from unittest.mock import patch

from apps.booking.models import SupplierAssignment
from apps.booking.services.assignment_service import AssignmentService

from .helpers import BookingTestCase


class AssignmentAtomicityTest(BookingTestCase):
    def test_assign_rolls_back_fully_on_late_failure(self):
        supplier = self._create_supplier()

        with patch(
            "apps.booking.services.assignment_service.EventPublisher.publish",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                AssignmentService.assign(order_id=self.order.id, supplier=supplier)

        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier)
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 0)

    def test_replace_rolls_back_fully_on_late_failure(self):
        s1 = self._create_supplier()
        s2 = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=s1)

        with patch(
            "apps.booking.services.assignment_service.EventPublisher.publish",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                AssignmentService.replace(order_id=self.order.id, new_supplier=s2)

        # Order must still point at s1 — the failed replace must not have partially applied.
        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, s1.id)
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 1)

    def test_cancel_rolls_back_fully_on_late_failure(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)

        with patch(
            "apps.booking.services.assignment_service.EventPublisher.publish",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                AssignmentService.cancel(order_id=self.order.id)

        # Order must still be assigned — the failed cancel must not have partially applied.
        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, supplier.id)
