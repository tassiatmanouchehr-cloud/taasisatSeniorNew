"""
Tests proving ExecutionService.close_session() denies an unauthorized actor
and produces zero business-side effects (no session/Order status change).
"""

from apps.execution.models import ExecutionSessionStatus
from apps.execution.services.session_service import ExecutionService
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.orders.models import OrderStatus

from .helpers import ExecutionTestCase


class ExecutionSessionPermissionEnforcementTest(ExecutionTestCase):
    def setUp(self):
        super().setUp()
        self.unauthorized_actor = make_actor(self.tenant, full_name="No Permission Actor")

    def _completed_session(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        return ExecutionService.complete_session(session_id=session.id)

    def test_close_session_denied_without_permission(self):
        session = self._completed_session()

        with self.assertRaises(PermissionDenied):
            ExecutionService.close_session(session_id=session.id, changed_by=self.unauthorized_actor)

        session.refresh_from_db()
        self.assertEqual(session.status, ExecutionSessionStatus.PROVIDER_COMPLETED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_PROGRESS)

    def test_close_session_allowed_with_permission(self):
        session = self._completed_session()
        grant_permissions(self.tenant, self.unauthorized_actor, ["execution.session.close"])

        closed = ExecutionService.close_session(session_id=session.id, changed_by=self.unauthorized_actor)

        self.assertEqual(closed.status, ExecutionSessionStatus.CLOSED)

    def test_close_session_still_works_with_no_actor_supplied(self):
        session = self._completed_session()
        closed = ExecutionService.close_session(session_id=session.id)
        self.assertEqual(closed.status, ExecutionSessionStatus.CLOSED)
