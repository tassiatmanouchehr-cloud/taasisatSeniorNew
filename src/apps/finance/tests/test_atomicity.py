"""
Tests proving finance service methods are wrapped in transaction.atomic():
a failure anywhere inside create_invoice_from_execution()/record_payment()/
post_entries()/create_batch() must roll back EVERYTHING, not leave partial
state behind.
"""

from unittest.mock import patch

from apps.finance.models import (
    FinancialDocument,
    FinancialObligation,
    LedgerEntry,
    LedgerEntryType,
    PaymentTransaction,
    SettlementBatch,
)
from apps.finance.services import (
    FinancialDocumentService,
    LedgerService,
    ObligationService,
    PaymentService,
    SettlementService,
)

from .helpers import FinanceTestCase

_PUBLISH_TARGET = "apps.kernel.services.event_publisher.EventPublisher.publish"


class FinanceAtomicityTest(FinanceTestCase):
    def test_create_invoice_rolls_back_fully_on_late_failure(self):
        session = self._close_execution_session()

        with patch(_PUBLISH_TARGET, side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            FinancialDocumentService.create_invoice_from_execution(
                execution_session_id=session.id,
                items=self._invoice_items(),
            )

        self.assertEqual(FinancialDocument.objects.filter(execution_session_id=session.id).count(), 0)

    def test_create_obligations_rolls_back_fully_on_late_failure(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )
        document = FinancialDocumentService.issue_document(document_id=document.id)

        with patch(_PUBLISH_TARGET, side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            ObligationService.create_obligations_for_document(document_id=document.id)

        self.assertEqual(FinancialObligation.objects.filter(source_document=document).count(), 0)

    def test_record_payment_rolls_back_fully_on_late_failure(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )
        document = FinancialDocumentService.issue_document(document_id=document.id)
        obligation = ObligationService.create_obligations_for_document(document_id=document.id)

        with patch(_PUBLISH_TARGET, side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            PaymentService.record_payment(
                payer_party_id=obligation.debtor_party_id,
                receiver_party_id=obligation.creditor_party_id,
                amount=obligation.amount,
                payment_method="ONLINE",
                obligation_id=obligation.id,
            )

        self.assertEqual(PaymentTransaction.objects.filter(obligation=obligation).count(), 0)
        obligation.refresh_from_db()
        self.assertEqual(obligation.status, "CREATED")

    def test_post_entries_rolls_back_fully_on_late_failure(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )
        payer = document.payer_party
        issuer = document.issuer_party

        with patch(_PUBLISH_TARGET, side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            LedgerService.post_entries(
                tenant_id=self.tenant.id,
                entries=[
                    {
                        "party_id": payer.id,
                        "entry_type": LedgerEntryType.DEBIT,
                        "account_code": "AR_CUSTOMER",
                        "amount": document.total_amount,
                        "source_document_id": document.id,
                    },
                    {
                        "party_id": issuer.id,
                        "entry_type": LedgerEntryType.CREDIT,
                        "account_code": "REVENUE",
                        "amount": document.total_amount,
                        "source_document_id": document.id,
                    },
                ],
            )

        self.assertEqual(LedgerEntry.objects.filter(source_document=document).count(), 0)

    def test_create_settlement_batch_rolls_back_fully_on_late_failure(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )
        document = FinancialDocumentService.issue_document(document_id=document.id)
        obligation = ObligationService.create_obligations_for_document(document_id=document.id)
        PaymentService.record_payment(
            payer_party_id=obligation.debtor_party_id,
            receiver_party_id=obligation.creditor_party_id,
            amount=obligation.amount,
            payment_method="ONLINE",
            obligation_id=obligation.id,
        )

        with patch(_PUBLISH_TARGET, side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            SettlementService.create_batch(tenant_id=self.tenant.id)

        self.assertEqual(SettlementBatch.objects.filter(tenant_id=self.tenant.id).count(), 0)
