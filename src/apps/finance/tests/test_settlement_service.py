"""Tests for SettlementService net-position calculation and batch creation."""

from decimal import Decimal

from apps.finance.models import SettlementBatchStatus, SettlementItemStatus
from apps.finance.services import FinancialDocumentService, ObligationService, PaymentService, SettlementService

from .helpers import FinanceTestCase


class SettlementServiceTest(FinanceTestCase):
    def _resolve_invoice(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id, items=self._invoice_items(),
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
        obligation.refresh_from_db()
        return document, obligation

    def test_calculate_net_position_from_resolved_obligations(self):
        document, obligation = self._resolve_invoice()

        net_positions = SettlementService.calculate_net_position(tenant_id=self.tenant.id)

        self.assertEqual(net_positions[obligation.creditor_party_id], obligation.amount)
        self.assertEqual(net_positions[obligation.debtor_party_id], -obligation.amount)

    def test_create_batch_materializes_settlement_items(self):
        document, obligation = self._resolve_invoice()

        batch = SettlementService.create_batch(tenant_id=self.tenant.id)

        self.assertEqual(batch.status, SettlementBatchStatus.CALCULATED)
        self.assertEqual(batch.items.count(), 2)
        self.assertEqual(batch.total_amount, obligation.amount * 2)

        creditor_item = batch.items.get(party_id=obligation.creditor_party_id)
        self.assertEqual(creditor_item.amount, obligation.amount)
        self.assertEqual(creditor_item.status, SettlementItemStatus.PENDING)

    def test_create_batch_excludes_unresolved_obligations(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id, items=self._invoice_items(),
        )
        document = FinancialDocumentService.issue_document(document_id=document.id)
        ObligationService.create_obligations_for_document(document_id=document.id)

        batch = SettlementService.create_batch(tenant_id=self.tenant.id)

        self.assertEqual(batch.items.count(), 0)
        self.assertEqual(batch.total_amount, Decimal("0"))
