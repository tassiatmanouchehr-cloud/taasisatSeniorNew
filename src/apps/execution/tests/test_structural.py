"""
Structural guarantee: ExecutionService must never write Order.status or
call order.save() directly — only apps.orders.services.status_machine may
do that. Mirrors the equivalent booking test
(test_assignment_service_never_assigns_order_directly).
"""

import inspect

from django.test import TestCase

from apps.execution.services import session_service as session_service_module


class ExecutionServiceStructuralTest(TestCase):
    def test_execution_service_never_writes_order_directly(self):
        source = inspect.getsource(session_service_module)
        self.assertNotIn("order.status =", source)
        self.assertNotIn("order.save(", source)
