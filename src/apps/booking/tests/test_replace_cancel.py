"""Tests for AssignmentService.replace() and AssignmentService.cancel()."""

from apps.booking.models import SupplierAssignment, SupplierAssignmentStatus
from apps.booking.services.assignment_service import AssignmentError, AssignmentService
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.kernel.models.event_outbox import EventOutbox
from apps.orders.services.status_machine import assign_supplier

from .helpers import BookingTestCase


class AssignmentServiceReplaceTest(BookingTestCase):
    def test_replace_creates_new_assignment_with_next_sequence(self):
        s1 = self._create_supplier()
        s2 = self._create_supplier()
        first = AssignmentService.assign(order_id=self.order.id, supplier=s1)
        second = AssignmentService.replace(order_id=self.order.id, new_supplier=s2)

        self.assertEqual(first.assignment_sequence, 1)
        self.assertEqual(second.assignment_sequence, 2)
        self.assertEqual(second.supplier_id, s2.id)

    def test_replace_marks_previous_as_replaced_and_links_superseded_by(self):
        s1 = self._create_supplier()
        s2 = self._create_supplier()
        first = AssignmentService.assign(order_id=self.order.id, supplier=s1)
        second = AssignmentService.replace(order_id=self.order.id, new_supplier=s2)

        first.refresh_from_db()
        self.assertEqual(first.status, SupplierAssignmentStatus.REPLACED)
        self.assertEqual(first.superseded_by_id, second.id)

    def test_replace_updates_order_assigned_supplier(self):
        s1 = self._create_supplier()
        s2 = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=s1)
        AssignmentService.replace(order_id=self.order.id, new_supplier=s2)

        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, s2.id)

    def test_replace_chain_across_three_suppliers(self):
        s1, s2, s3 = self._create_supplier(), self._create_supplier(), self._create_supplier()
        a1 = AssignmentService.assign(order_id=self.order.id, supplier=s1)
        a2 = AssignmentService.replace(order_id=self.order.id, new_supplier=s2)
        a3 = AssignmentService.replace(order_id=self.order.id, new_supplier=s3)

        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertEqual(a1.status, SupplierAssignmentStatus.REPLACED)
        self.assertEqual(a1.superseded_by_id, a2.id)
        self.assertEqual(a2.status, SupplierAssignmentStatus.REPLACED)
        self.assertEqual(a2.superseded_by_id, a3.id)
        self.assertEqual(a3.status, SupplierAssignmentStatus.ASSIGNED)
        self.assertEqual(a3.assignment_sequence, 3)

    def test_replace_rejects_cross_tenant_supplier(self):
        s1 = self._create_supplier()
        other_supplier = self._create_supplier(tenant=self.other_tenant)
        AssignmentService.assign(order_id=self.order.id, supplier=s1)
        with self.assertRaises(AssignmentError):
            AssignmentService.replace(order_id=self.order.id, new_supplier=other_supplier)

    def test_replace_blocked_when_reassignment_disabled(self):
        config_key = ConfigurationKey.objects.create(
            key="booking.reassignment.enabled", owner_module="M03",
            scope_level=ScopeLevel.TENANT, value_type=ValueType.BOOLEAN, default_value=True,
        )
        ConfigurationValue.objects.create(
            tenant_id=self.tenant.id, config_key=config_key, scope_type=ScopeLevel.TENANT,
            value=False, is_active=True,
        )
        s1 = self._create_supplier()
        s2 = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=s1)
        with self.assertRaises(AssignmentError):
            AssignmentService.replace(order_id=self.order.id, new_supplier=s2)

        # Nothing should have changed — order still assigned to s1, no new row.
        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, s1.id)
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 1)

    def test_replace_emits_versioned_event(self):
        s1 = self._create_supplier()
        s2 = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=s1)
        AssignmentService.replace(order_id=self.order.id, new_supplier=s2)
        event = EventOutbox.objects.filter(event_type="Booking.Assignment.Replaced.v1").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["previous_supplier_id"], str(s1.id))
        self.assertEqual(event.payload["new_supplier_id"], str(s2.id))


class AssignmentServiceCancelTest(BookingTestCase):
    def test_cancel_marks_current_assignment_cancelled(self):
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        result = AssignmentService.cancel(order_id=self.order.id)

        self.assertEqual(result.id, assignment.id)
        result.refresh_from_db()
        self.assertEqual(result.status, SupplierAssignmentStatus.CANCELLED)

    def test_cancel_clears_order_assigned_supplier(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        AssignmentService.cancel(order_id=self.order.id)

        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier)

    def test_cancel_merges_metadata(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=supplier, metadata={"a": 1})
        result = AssignmentService.cancel(order_id=self.order.id, metadata={"b": 2})
        result.refresh_from_db()
        self.assertEqual(result.metadata, {"a": 1, "b": 2})

    def test_cancel_without_prior_supplier_assignment_still_works(self):
        """An order assigned via the raw status_machine (bypassing booking) can still be cancelled."""
        supplier = self._create_supplier()
        assign_supplier(order_id=self.order.id, supplier=supplier)

        result = AssignmentService.cancel(order_id=self.order.id)

        self.assertIsNone(result)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier)

    def test_cancel_emits_versioned_event(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        AssignmentService.cancel(order_id=self.order.id)
        self.assertTrue(EventOutbox.objects.filter(event_type="Booking.Assignment.Cancelled.v1").exists())
