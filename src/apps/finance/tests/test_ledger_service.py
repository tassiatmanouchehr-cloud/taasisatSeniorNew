"""Tests for LedgerService: balanced posting, unbalanced rejection, immutability."""

from decimal import Decimal

from apps.finance.models import LedgerEntry, LedgerEntryType
from apps.finance.services import FinanceError, FinancialDocumentService, LedgerService

from .helpers import FinanceTestCase


class LedgerServiceTest(FinanceTestCase):
    def _document_and_parties(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )
        payer = document.payer_party
        issuer = document.issuer_party
        return document, payer, issuer

    def test_post_entries_creates_balanced_group(self):
        document, payer, issuer = self._document_and_parties()

        entries = LedgerService.post_entries(
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

        self.assertEqual(len(entries), 2)
        self.assertEqual(LedgerEntry.objects.filter(entry_group_id=entries[0].entry_group_id).count(), 2)

    def test_post_entries_rejects_unbalanced_posting(self):
        document, payer, issuer = self._document_and_parties()

        with self.assertRaises(FinanceError):
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
                        "amount": Decimal("1"),
                        "source_document_id": document.id,
                    },
                ],
            )
        self.assertEqual(LedgerEntry.objects.count(), 0)

    def test_post_entries_rejects_entry_without_reference(self):
        document, payer, issuer = self._document_and_parties()

        with self.assertRaises(FinanceError):
            LedgerService.post_entries(
                tenant_id=self.tenant.id,
                entries=[
                    {
                        "party_id": payer.id,
                        "entry_type": LedgerEntryType.DEBIT,
                        "account_code": "AR",
                        "amount": Decimal("1"),
                    },
                    {
                        "party_id": issuer.id,
                        "entry_type": LedgerEntryType.CREDIT,
                        "account_code": "REV",
                        "amount": Decimal("1"),
                    },
                ],
            )

    def test_ledger_entry_is_immutable(self):
        document, payer, issuer = self._document_and_parties()

        entries = LedgerService.post_entries(
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
        entry = LedgerEntry.objects.get(id=entries[0].id)

        with self.assertRaises(ValueError):
            entry.amount = Decimal("1")
            entry.save()

        with self.assertRaises(ValueError):
            entry.delete()
