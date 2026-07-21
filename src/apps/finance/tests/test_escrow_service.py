"""Tests for EscrowService hold/release/refund."""

from apps.finance.models import EscrowStatus
from apps.finance.services import EscrowService, FinanceError, FinancialDocumentService

from .helpers import FinanceTestCase


class EscrowServiceTest(FinanceTestCase):
    def _draft_document(self):
        session = self._close_execution_session()
        return FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

    def test_hold_creates_held_escrow(self):
        document = self._draft_document()

        escrow = EscrowService.hold(
            source_document_id=document.id,
            payer_party_id=document.payer_party_id,
            amount=document.total_amount,
        )

        self.assertEqual(escrow.status, EscrowStatus.HELD)
        self.assertEqual(escrow.amount, document.total_amount)

    def test_release_transitions_held_to_released(self):
        document = self._draft_document()
        escrow = EscrowService.hold(
            source_document_id=document.id,
            payer_party_id=document.payer_party_id,
            amount=document.total_amount,
        )

        released = EscrowService.release(escrow_id=escrow.id)

        self.assertEqual(released.status, EscrowStatus.RELEASED)
        self.assertIsNotNone(released.released_at)

    def test_refund_transitions_held_to_refunded(self):
        document = self._draft_document()
        escrow = EscrowService.hold(
            source_document_id=document.id,
            payer_party_id=document.payer_party_id,
            amount=document.total_amount,
        )

        refunded = EscrowService.refund(escrow_id=escrow.id)

        self.assertEqual(refunded.status, EscrowStatus.REFUNDED)

    def test_cannot_release_an_already_released_escrow(self):
        document = self._draft_document()
        escrow = EscrowService.hold(
            source_document_id=document.id,
            payer_party_id=document.payer_party_id,
            amount=document.total_amount,
        )
        EscrowService.release(escrow_id=escrow.id)

        with self.assertRaises(FinanceError):
            EscrowService.release(escrow_id=escrow.id)
