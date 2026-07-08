"""
Tests proving ExecutionService methods are wrapped in transaction.atomic():
a failure anywhere inside create_session()/start_session()/complete_session()/
close_session() must roll back EVERYTHING — both the orders.status_machine
mutation (where applicable) and the ExecutionSession row change — not leave
partial state behind.
"""

from unittest.mock import patch

from apps.execution.models import ExecutionSession, ExecutionSessionStatus
from apps.execution.services.session_service import ExecutionService
from apps.orders.models import OrderStatus

from .helpers import ExecutionTestCase


class ExecutionAtomicityTest(ExecutionTestCase):
    def test_create_session_rolls_back_fully_on_late_failure(self):
        with patch(
            "apps.execution.services.session_service.EventPublisher.publish",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

        self.assertEqual(ExecutionSession.objects.filter(order=self.order).count(), 0)

    def test_start_session_rolls_back_fully_on_late_failure(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

        with patch(
            "apps.execution.services.session_service.EventPublisher.publish",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                ExecutionService.start_session(session_id=session.id)

        session.refresh_from_db()
        self.assertEqual(session.status, ExecutionSessionStatus.SCHEDULED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.WAITING_SERVICE)

    def test_complete_session_rolls_back_fully_on_late_failure(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=session.id)

        with patch(
            "apps.execution.services.session_service.EventPublisher.publish",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                ExecutionService.complete_session(session_id=session.id)

        session.refresh_from_db()
        self.assertEqual(session.status, ExecutionSessionStatus.IN_PROGRESS)

    def test_close_session_rolls_back_fully_on_late_failure(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)

        with patch(
            "apps.execution.services.session_service.EventPublisher.publish",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                ExecutionService.close_session(session_id=session.id)

        session.refresh_from_db()
        self.assertEqual(session.status, ExecutionSessionStatus.PROVIDER_COMPLETED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_PROGRESS)
