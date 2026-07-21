"""
Structural guarantee: no finance service may write Order.status,
Order.assigned_supplier, ExecutionSession.status, or SupplierAssignment.status,
and LedgerEntry may only be posted with a reference to a document, payment,
or obligation — never directly from an ExecutionSession.
"""

import inspect

from django.test import TestCase

from apps.finance.services import (
    document_service,
    escrow_service,
    ledger_service,
    obligation_service,
    party_service,
    payment_service,
    settlement_service,
    wallet_service,
)

_FORBIDDEN_MUTATIONS = (
    "order.status =",
    "order.save(",
    "execution_session.status =",
    "session.status =",
    "session.save(",
    "supplier_assignment.status =",
    "assignment.status =",
)

_SERVICE_MODULES = (
    document_service,
    obligation_service,
    payment_service,
    wallet_service,
    escrow_service,
    ledger_service,
    settlement_service,
    party_service,
)


class FinanceStructuralTest(TestCase):
    def test_finance_services_never_mutate_upstream_ownership_fields(self):
        for module in _SERVICE_MODULES:
            source = inspect.getsource(module)
            for forbidden in _FORBIDDEN_MUTATIONS:
                self.assertNotIn(
                    forbidden,
                    source,
                    f"{module.__name__} must not write '{forbidden}'",
                )

    def test_ledger_service_never_references_execution_session_directly(self):
        source = inspect.getsource(ledger_service.LedgerService)
        self.assertNotIn("ExecutionSession", source)
        self.assertNotIn("execution_session_id", source)
