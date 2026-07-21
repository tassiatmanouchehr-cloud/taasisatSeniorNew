"""
Tests proving the 5 gated finance actions (issue_document, lock_document,
record_payment, post_entries, create_batch) deny an unauthorized actor and
produce zero business-side effects when denied.
"""

from apps.finance.models import (
    FinancialDocumentStatus,
    LedgerEntry,
    LedgerEntryType,
    PaymentTransaction,
    SettlementBatch,
)
from apps.finance.services import FinancialDocumentService, LedgerService, PaymentService, SettlementService
from apps.finance.services.obligation_service import ObligationService
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor

from .helpers import FinanceTestCase


class FinancePermissionEnforcementTest(FinanceTestCase):
    def setUp(self):
        super().setUp()
        self.unauthorized_actor = make_actor(self.tenant, full_name="No Permission Actor")

    def _draft_document(self):
        session = self._close_execution_session()
        return FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

    def test_issue_document_denied_without_permission(self):
        document = self._draft_document()

        with self.assertRaises(PermissionDenied):
            FinancialDocumentService.issue_document(document_id=document.id, changed_by=self.unauthorized_actor)

        document.refresh_from_db()
        self.assertEqual(document.status, FinancialDocumentStatus.DRAFT)
        self.assertIsNone(document.issued_at)

    def test_issue_document_allowed_with_permission(self):
        document = self._draft_document()
        grant_permissions(self.tenant, self.unauthorized_actor, ["finance.document.issue"])

        issued = FinancialDocumentService.issue_document(document_id=document.id, changed_by=self.unauthorized_actor)

        self.assertEqual(issued.status, FinancialDocumentStatus.ISSUED)

    def test_lock_document_denied_without_permission(self):
        document = self._draft_document()
        FinancialDocumentService.issue_document(document_id=document.id)

        with self.assertRaises(PermissionDenied):
            FinancialDocumentService.lock_document(document_id=document.id, changed_by=self.unauthorized_actor)

        document.refresh_from_db()
        self.assertEqual(document.status, FinancialDocumentStatus.ISSUED)
        self.assertIsNone(document.locked_at)

    def test_record_payment_denied_without_permission(self):
        document = self._draft_document()
        document = FinancialDocumentService.issue_document(document_id=document.id)
        obligation = ObligationService.create_obligations_for_document(document_id=document.id)

        with self.assertRaises(PermissionDenied):
            PaymentService.record_payment(
                payer_party_id=obligation.debtor_party_id,
                receiver_party_id=obligation.creditor_party_id,
                amount=obligation.amount,
                payment_method="ONLINE",
                obligation_id=obligation.id,
                recorded_by=self.unauthorized_actor,
            )

        self.assertEqual(PaymentTransaction.objects.filter(obligation=obligation).count(), 0)
        obligation.refresh_from_db()
        self.assertEqual(obligation.status, "CREATED")

    def test_post_entries_denied_without_permission(self):
        document = self._draft_document()
        payer = document.payer_party
        issuer = document.issuer_party

        with self.assertRaises(PermissionDenied):
            LedgerService.post_entries(
                tenant_id=self.tenant.id,
                actor=self.unauthorized_actor,
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

    def test_create_settlement_batch_denied_without_permission(self):
        with self.assertRaises(PermissionDenied):
            SettlementService.create_batch(tenant_id=self.tenant.id, actor=self.unauthorized_actor)

        self.assertEqual(SettlementBatch.objects.filter(tenant_id=self.tenant.id).count(), 0)

    def test_gated_methods_still_work_with_no_actor_supplied(self):
        """Backward compatibility: internal/system calls without an actor keep working."""
        document = self._draft_document()
        issued = FinancialDocumentService.issue_document(document_id=document.id)
        self.assertEqual(issued.status, FinancialDocumentStatus.ISSUED)
