"""
Tests for AssignmentService.assign() — creation path.

Critically verifies AssignmentService never assigns Order.assigned_supplier
itself — that stays exclusively owned by
apps.orders.services.status_machine.assign_supplier().
"""

import inspect

from apps.booking.models import AssignmentSource, SupplierAssignment, SupplierAssignmentStatus
from apps.booking.services import assignment_service as assignment_service_module
from apps.booking.services.assignment_service import AssignmentError, AssignmentService
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.kernel.models.event_outbox import EventOutbox
from apps.matching.models import MatchCandidateStatus

from .helpers import BookingTestCase


class AssignmentServiceAssignTest(BookingTestCase):
    def test_assign_delegates_order_mutation_to_status_machine(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, supplier.id)
        self.assertEqual(self.order.status, "waiting_service")

    def test_assign_creates_supplier_assignment_row(self):
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 1)
        self.assertEqual(assignment.supplier_id, supplier.id)
        self.assertEqual(assignment.tenant_id, self.tenant.id)
        self.assertEqual(assignment.assignment_sequence, 1)

    def test_assign_default_status_is_assigned(self):
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        self.assertEqual(assignment.status, SupplierAssignmentStatus.ASSIGNED)

    def test_assign_status_confirmed_when_auto_accept_enabled(self):
        config_key = ConfigurationKey.objects.create(
            key="booking.assignment.auto_accept_enabled",
            owner_module="M03",
            scope_level=ScopeLevel.TENANT,
            value_type=ValueType.BOOLEAN,
            default_value=False,
        )
        ConfigurationValue.objects.create(
            tenant_id=self.tenant.id,
            config_key=config_key,
            scope_type=ScopeLevel.TENANT,
            value=True,
            is_active=True,
        )
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        self.assertEqual(assignment.status, SupplierAssignmentStatus.CONFIRMED)

    def test_manual_assignment_source_is_default(self):
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        self.assertEqual(assignment.assignment_source, AssignmentSource.MANUAL)

    def test_matching_assignment_source_inferred_from_candidate(self):
        supplier = self._create_supplier()
        candidate = self._create_match_candidate(supplier=supplier)
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=supplier, match_candidate=candidate)
        self.assertEqual(assignment.assignment_source, AssignmentSource.MATCHING)

    def test_explicit_assignment_source_overrides_inference(self):
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(
            order_id=self.order.id,
            supplier=supplier,
            assignment_source=AssignmentSource.API,
        )
        self.assertEqual(assignment.assignment_source, AssignmentSource.API)

    def test_assign_with_match_candidate_marks_it_selected(self):
        supplier = self._create_supplier()
        candidate = self._create_match_candidate(supplier=supplier)
        AssignmentService.assign(order_id=self.order.id, supplier=supplier, match_candidate=candidate)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, MatchCandidateStatus.SELECTED)

    def test_metadata_json_is_stored(self):
        supplier = self._create_supplier()
        assignment = AssignmentService.assign(
            order_id=self.order.id,
            supplier=supplier,
            metadata={"note": "urgent case"},
        )
        assignment.refresh_from_db()
        self.assertEqual(assignment.metadata, {"note": "urgent case"})

    def test_assign_rejects_cross_tenant_supplier(self):
        other_supplier = self._create_supplier(tenant=self.other_tenant)
        with self.assertRaises(AssignmentError):
            AssignmentService.assign(order_id=self.order.id, supplier=other_supplier)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier)
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 0)

    def test_assign_emits_versioned_created_event(self):
        supplier = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        event = EventOutbox.objects.filter(event_type="Booking.Assignment.Created.v1").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.source_module, "M03")
        self.assertEqual(event.payload["order_id"], str(self.order.id))
        self.assertEqual(event.payload["supplier_id"], str(supplier.id))

    def test_assignment_service_never_assigns_order_directly(self):
        """Structural guarantee: AssignmentService must only ever call into status_machine."""
        source = inspect.getsource(assignment_service_module)
        self.assertNotIn("order.assigned_supplier =", source)
        self.assertNotIn(".assigned_supplier = ", source)
        self.assertNotIn("order.save(", source)
