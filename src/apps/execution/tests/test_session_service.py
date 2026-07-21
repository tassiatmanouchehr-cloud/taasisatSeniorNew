"""Tests for ExecutionService.create_session() and start_session()."""

from apps.booking.models import SupplierAssignmentStatus
from apps.execution.models import ExecutionSession, ExecutionSessionStatus, ExecutionSource
from apps.execution.services.session_service import ExecutionError, ExecutionService
from apps.kernel.models.event_outbox import EventOutbox
from apps.orders.models import OrderStatus

from .helpers import ExecutionTestCase


class CreateSessionTest(ExecutionTestCase):
    def test_create_session_sets_scheduled_status(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        self.assertEqual(session.status, ExecutionSessionStatus.SCHEDULED)

    def test_create_session_links_order_and_assignment(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        self.assertEqual(session.order_id, self.order.id)
        self.assertEqual(session.supplier_assignment_id, self.supplier_assignment.id)
        self.assertEqual(session.tenant_id, self.order.tenant_id)

    def test_create_session_sequence_starts_at_one(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        self.assertEqual(session.execution_sequence, 1)

    def test_create_session_default_source_is_booking(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        self.assertEqual(session.execution_source, ExecutionSource.BOOKING)

    def test_create_session_explicit_source_override(self):
        session = ExecutionService.create_session(
            supplier_assignment=self.supplier_assignment,
            execution_source=ExecutionSource.MANUAL,
        )
        self.assertEqual(session.execution_source, ExecutionSource.MANUAL)

    def test_create_session_stores_context_snapshot(self):
        session = ExecutionService.create_session(
            supplier_assignment=self.supplier_assignment,
            context_snapshot={"note": "priority case"},
        )
        session.refresh_from_db()
        self.assertEqual(session.context_snapshot, {"note": "priority case"})

    def test_create_session_rejects_cancelled_assignment(self):
        from apps.booking.services.assignment_service import AssignmentService

        AssignmentService.cancel(order_id=self.order.id)
        self.supplier_assignment.refresh_from_db()
        self.assertEqual(self.supplier_assignment.status, SupplierAssignmentStatus.CANCELLED)

        with self.assertRaises(ExecutionError):
            ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

    def test_create_session_emits_created_event(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        event = EventOutbox.objects.filter(event_type="Execution.Session.Created.v1").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.source_module, "M04")
        self.assertEqual(event.payload["order_id"], str(self.order.id))
        self.assertEqual(event.payload["supplier_assignment_id"], str(self.supplier_assignment.id))

    def test_duplicate_sequence_rejected_by_db(self):
        from django.db import IntegrityError, transaction

        ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExecutionSession.objects.create(
                tenant_id=self.order.tenant_id,
                order=self.order,
                supplier_assignment=self.supplier_assignment,
                status=ExecutionSessionStatus.SCHEDULED,
                execution_source=ExecutionSource.MANUAL,
                execution_sequence=1,
            )


class StartSessionTest(ExecutionTestCase):
    def setUp(self):
        super().setUp()
        self.session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

    def test_start_session_transitions_to_in_progress(self):
        session = ExecutionService.start_session(session_id=self.session.id)
        self.assertEqual(session.status, ExecutionSessionStatus.IN_PROGRESS)

    def test_start_session_sets_started_at(self):
        session = ExecutionService.start_session(session_id=self.session.id)
        self.assertIsNotNone(session.started_at)

    def test_start_session_delegates_to_status_machine(self):
        ExecutionService.start_session(session_id=self.session.id)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_PROGRESS)
        self.assertIsNotNone(self.order.started_at)

    def test_start_session_emits_started_event(self):
        ExecutionService.start_session(session_id=self.session.id)
        event = EventOutbox.objects.filter(event_type="Execution.Session.Started.v1").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["order_id"], str(self.order.id))

    def test_start_session_requires_scheduled_status(self):
        ExecutionService.start_session(session_id=self.session.id)
        with self.assertRaises(ExecutionError):
            ExecutionService.start_session(session_id=self.session.id)
