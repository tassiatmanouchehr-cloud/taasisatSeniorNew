"""Tests for PaymentService."""

from decimal import Decimal

from apps.finance.models import FinancialDocumentStatus, ObligationStatus, PaymentStatus
from apps.finance.services import FinancialDocumentService, ObligationService, PaymentService

from .helpers import FinanceTestCase


class PaymentServiceTest(FinanceTestCase):
    def _resolved_obligation(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id, items=self._invoice_items(),
        )
        document = FinancialDocumentService.issue_document(document_id=document.id)
        obligation = ObligationService.create_obligations_for_document(document_id=document.id)
        return document, obligation

    def test_payment_partially_resolves_obligation(self):
        document, obligation = self._resolved_obligation()
        half = obligation.amount / 2

        PaymentService.record_payment(
            payer_party_id=obligation.debtor_party_id,
            receiver_party_id=obligation.creditor_party_id,
            amount=half,
            payment_method="CASH",
            obligation_id=obligation.id,
        )

        obligation.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(obligation.status, ObligationStatus.PARTIALLY_RESOLVED)
        self.assertEqual(document.status, FinancialDocumentStatus.PARTIALLY_PAID)

    def test_payment_fully_resolves_obligation(self):
        document, obligation = self._resolved_obligation()

        payment = PaymentService.record_payment(
            payer_party_id=obligation.debtor_party_id,
            receiver_party_id=obligation.creditor_party_id,
            amount=obligation.amount,
            payment_method="ONLINE",
        )

        obligation.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.SUCCEEDED)
        # No obligation_id was passed above; resolve it explicitly to prove
        # resolution only happens when a payment is tied to the obligation.
        self.assertEqual(obligation.status, ObligationStatus.CREATED)

        PaymentService.record_payment(
            payer_party_id=obligation.debtor_party_id,
            receiver_party_id=obligation.creditor_party_id,
            amount=obligation.amount,
            payment_method="ONLINE",
            obligation_id=obligation.id,
        )

        obligation.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(obligation.status, ObligationStatus.RESOLVED)
        self.assertIsNotNone(obligation.resolved_at)
        self.assertEqual(document.status, FinancialDocumentStatus.PAID)
        self.assertIsNotNone(document.paid_at)

    def test_failed_payment_does_not_resolve_obligation(self):
        _, obligation = self._resolved_obligation()

        PaymentService.record_payment(
            payer_party_id=obligation.debtor_party_id,
            receiver_party_id=obligation.creditor_party_id,
            amount=obligation.amount,
            payment_method="ONLINE",
            obligation_id=obligation.id,
            status=PaymentStatus.FAILED,
        )

        obligation.refresh_from_db()
        self.assertEqual(obligation.status, ObligationStatus.CREATED)
