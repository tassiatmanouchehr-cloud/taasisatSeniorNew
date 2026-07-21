"""Tests for ExecutionService.complete_session() and close_session()."""

from apps.execution.models import ExecutionSessionStatus
from apps.execution.services.session_service import ExecutionError, ExecutionService
from apps.kernel.models.event_outbox import EventOutbox
from apps.orders.models import OrderStatus

from .helpers import ExecutionTestCase


class CompleteSessionTest(ExecutionTestCase):
    def setUp(self):
        super().setUp()
        self.session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=self.session.id)

    def test_complete_session_transitions_to_provider_completed(self):
        session = ExecutionService.complete_session(session_id=self.session.id)
        self.assertEqual(session.status, ExecutionSessionStatus.PROVIDER_COMPLETED)

    def test_complete_session_sets_provider_completed_at(self):
        session = ExecutionService.complete_session(session_id=self.session.id)
        self.assertIsNotNone(session.provider_completed_at)

    def test_complete_session_does_not_close_order(self):
        """PROVIDER_COMPLETED is a provider declaration only — Order must stay in_progress."""
        ExecutionService.complete_session(session_id=self.session.id)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_PROGRESS)
        self.assertIsNone(self.order.completed_at)

    def test_complete_session_emits_completed_event(self):
        ExecutionService.complete_session(session_id=self.session.id)
        event = EventOutbox.objects.filter(event_type="Execution.Session.Completed.v1").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["order_id"], str(self.order.id))

    def test_complete_session_requires_in_progress_status(self):
        ExecutionService.complete_session(session_id=self.session.id)
        with self.assertRaises(ExecutionError):
            ExecutionService.complete_session(session_id=self.session.id)


class CloseSessionTest(ExecutionTestCase):
    def setUp(self):
        super().setUp()
        self.session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=self.session.id)
        ExecutionService.complete_session(session_id=self.session.id)

    def test_close_session_transitions_to_closed(self):
        session = ExecutionService.close_session(session_id=self.session.id)
        self.assertEqual(session.status, ExecutionSessionStatus.CLOSED)

    def test_close_session_sets_closed_at(self):
        session = ExecutionService.close_session(session_id=self.session.id)
        self.assertIsNotNone(session.closed_at)

    def test_close_session_completes_order(self):
        ExecutionService.close_session(session_id=self.session.id)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.COMPLETED)
        self.assertIsNotNone(self.order.completed_at)

    def test_close_session_emits_closed_event(self):
        ExecutionService.close_session(session_id=self.session.id)
        event = EventOutbox.objects.filter(event_type="Execution.Session.Closed.v1").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["order_id"], str(self.order.id))

    def test_close_session_requires_closable_status(self):
        ExecutionService.close_session(session_id=self.session.id)
        with self.assertRaises(ExecutionError):
            ExecutionService.close_session(session_id=self.session.id)

    def test_close_session_allowed_from_customer_pending(self):
        """CUSTOMER_PENDING is reserved for a future confirmation workflow but close() must accept it."""
        self.session.status = ExecutionSessionStatus.CUSTOMER_PENDING
        self.session.save(update_fields=["status"])

        session = ExecutionService.close_session(session_id=self.session.id)
        self.assertEqual(session.status, ExecutionSessionStatus.CLOSED)

    def test_cannot_close_directly_from_in_progress(self):
        other_supplier = self._create_supplier()
        from apps.booking.services.assignment_service import AssignmentService
        from apps.orders.services.order_creation import create_operator_order

        order2 = create_operator_order(
            service_category_id=self.category.id,
            description="x",
            phone="0912",
            address="addr",
            tenant_id=self.tenant.id,
        )
        assignment2 = AssignmentService.assign(order_id=order2.id, supplier=other_supplier)
        session2 = ExecutionService.create_session(supplier_assignment=assignment2)
        ExecutionService.start_session(session_id=session2.id)

        with self.assertRaises(ExecutionError):
            ExecutionService.close_session(session_id=session2.id)
