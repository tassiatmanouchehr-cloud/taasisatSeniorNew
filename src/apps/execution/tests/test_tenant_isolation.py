"""Tests for ExecutionSession tenant isolation."""

from apps.execution.models import ExecutionSession
from apps.execution.services.session_service import ExecutionService

from .helpers import ExecutionTestCase


class ExecutionSessionTenantIsolationTest(ExecutionTestCase):
    def test_for_tenant_scopes_execution_sessions(self):
        ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

        self.assertEqual(ExecutionSession.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(ExecutionSession.objects.for_tenant(self.other_tenant.id).count(), 0)

    def test_execution_session_tenant_matches_order_tenant(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        self.assertEqual(session.tenant_id, self.order.tenant_id)
