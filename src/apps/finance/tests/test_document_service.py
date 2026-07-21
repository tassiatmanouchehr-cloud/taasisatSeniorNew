"""Tests for FinancialDocumentService (invoice creation and lifecycle transitions)."""

from decimal import Decimal

from apps.finance.models import FinancialDocumentStatus, FinancialDocumentType
from apps.finance.services import FinanceError, FinancialDocumentService

from .helpers import FinanceTestCase


class FinancialDocumentServiceTest(FinanceTestCase):
    def test_create_invoice_from_closed_execution_session(self):
        session = self._close_execution_session()

        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        self.assertEqual(document.document_type, FinancialDocumentType.INVOICE)
        self.assertEqual(document.status, FinancialDocumentStatus.DRAFT)
        self.assertEqual(document.execution_session_id, session.id)
        self.assertEqual(document.order_id, self.order.id)
        self.assertEqual(document.payer_party.linked_entity_id, self.customer_profile.id)
        self.assertEqual(document.beneficiary_party.linked_entity_id, self.supplier.id)

    def test_create_invoice_rejected_if_execution_session_not_closed(self):
        from apps.execution.services.session_service import ExecutionService

        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

        with self.assertRaises(FinanceError):
            FinancialDocumentService.create_invoice_from_execution(
                execution_session_id=session.id,
                items=self._invoice_items(),
            )

    def test_invoice_items_total_calculation(self):
        session = self._close_execution_session()

        items = [
            {"item_type": "SERVICE", "description": "Visit", "quantity": 2, "unit_price": "500000"},
            {"item_type": "TRAVEL", "description": "Travel", "quantity": 1, "unit_price": "50000"},
            {"item_type": "DISCOUNT", "description": "Loyalty discount", "quantity": 1, "unit_price": "-100000"},
            {"item_type": "TAX", "description": "VAT", "quantity": 1, "unit_price": "45000"},
        ]
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=items,
        )

        self.assertEqual(document.subtotal_amount, Decimal("1050000"))
        self.assertEqual(document.discount_amount, Decimal("100000"))
        self.assertEqual(document.tax_amount, Decimal("45000"))
        self.assertEqual(document.total_amount, Decimal("995000"))
        self.assertEqual(document.items.count(), 4)

    def test_pricing_snapshot_is_stored(self):
        session = self._close_execution_session()

        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        self.assertIn("items", document.pricing_snapshot)
        self.assertEqual(len(document.pricing_snapshot["items"]), 2)
        self.assertEqual(document.pricing_snapshot["total_amount"], str(document.total_amount))

    def test_issue_document_transitions_draft_to_issued(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        issued = FinancialDocumentService.issue_document(document_id=document.id)

        self.assertEqual(issued.status, FinancialDocumentStatus.ISSUED)
        self.assertIsNotNone(issued.issued_at)

    def test_lock_document_transitions_issued_to_locked(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )
        FinancialDocumentService.issue_document(document_id=document.id)

        locked = FinancialDocumentService.lock_document(document_id=document.id)

        self.assertEqual(locked.status, FinancialDocumentStatus.LOCKED)
        self.assertIsNotNone(locked.locked_at)

    def test_cannot_lock_an_already_locked_document(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )
        FinancialDocumentService.issue_document(document_id=document.id)
        FinancialDocumentService.lock_document(document_id=document.id)

        with self.assertRaises(FinanceError):
            FinancialDocumentService.lock_document(document_id=document.id)

    def test_cancel_document(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        cancelled = FinancialDocumentService.cancel_document(document_id=document.id)

        self.assertEqual(cancelled.status, FinancialDocumentStatus.CANCELLED)

    def test_create_supplemental_invoice(self):
        session = self._close_execution_session()

        document = FinancialDocumentService.create_supplemental_invoice(
            execution_session_id=session.id,
            items=[{"item_type": "EXTRA_SERVICE", "description": "Extra hour", "quantity": 1, "unit_price": "200000"}],
        )

        self.assertEqual(document.document_type, FinancialDocumentType.SUPPLEMENTAL_INVOICE)
        self.assertEqual(document.total_amount, Decimal("200000"))
