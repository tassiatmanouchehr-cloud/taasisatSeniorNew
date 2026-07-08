"""Tests for ObligationService."""

from apps.finance.models import ObligationStatus
from apps.finance.services import FinanceError, FinancialDocumentService, ObligationService

from .helpers import FinanceTestCase


class ObligationServiceTest(FinanceTestCase):
    def _issued_document(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id, items=self._invoice_items(),
        )
        return FinancialDocumentService.issue_document(document_id=document.id)

    def test_create_obligations_for_document(self):
        document = self._issued_document()

        obligation = ObligationService.create_obligations_for_document(document_id=document.id)

        self.assertEqual(obligation.source_document_id, document.id)
        self.assertEqual(obligation.debtor_party_id, document.payer_party_id)
        self.assertEqual(obligation.creditor_party_id, document.issuer_party_id)
        self.assertEqual(obligation.amount, document.total_amount)
        self.assertEqual(obligation.status, ObligationStatus.CREATED)

    def test_create_obligations_rejected_for_draft_document(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id, items=self._invoice_items(),
        )

        with self.assertRaises(FinanceError):
            ObligationService.create_obligations_for_document(document_id=document.id)
