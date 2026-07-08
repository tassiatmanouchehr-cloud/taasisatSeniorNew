"""
Regression tests: FinancialDocument must be immutable at the model level
once it has left DRAFT (issued or locked) — updates are restricted to the
lifecycle bookkeeping fields (status/issued_at/locked_at/paid_at/updated_at)
and deletes are rejected outright. DRAFT documents remain freely editable
and deletable, and creation is unaffected.
"""

from decimal import Decimal

from apps.finance.models import FinancialDocument
from apps.finance.services import FinancialDocumentService

from .helpers import FinanceTestCase


class FinancialDocumentImmutabilityTest(FinanceTestCase):
    def _draft_document(self):
        session = self._close_execution_session()
        return FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id, items=self._invoice_items(),
        )

    def test_creation_still_works_normally(self):
        document = self._draft_document()
        self.assertIsNotNone(document.pk)
        self.assertTrue(FinancialDocument.objects.filter(id=document.id).exists())

    def test_draft_document_can_be_updated_freely(self):
        document = self._draft_document()
        document.subtotal_amount = Decimal("1")
        document.save()  # no update_fields restriction while still DRAFT

        document.refresh_from_db()
        self.assertEqual(document.subtotal_amount, Decimal("1"))

    def test_draft_document_can_be_deleted(self):
        document = self._draft_document()
        document_id = document.id
        document.delete()

        self.assertFalse(FinancialDocument.objects.filter(id=document_id).exists())

    def test_issued_document_rejects_content_field_update(self):
        document = self._draft_document()
        FinancialDocumentService.issue_document(document_id=document.id)
        document.refresh_from_db()

        document.total_amount = Decimal("1")
        with self.assertRaises(ValueError):
            document.save(update_fields=["total_amount"])

    def test_issued_document_rejects_full_save_without_update_fields(self):
        document = self._draft_document()
        FinancialDocumentService.issue_document(document_id=document.id)
        document.refresh_from_db()

        with self.assertRaises(ValueError):
            document.save()

    def test_issued_document_allows_lifecycle_field_update(self):
        document = self._draft_document()
        FinancialDocumentService.issue_document(document_id=document.id)
        document.refresh_from_db()

        # Mirrors exactly what FinancialDocumentService.lock_document() does.
        document.status = "LOCKED"
        document.save(update_fields=["status", "locked_at", "updated_at"])

        document.refresh_from_db()
        self.assertEqual(document.status, "LOCKED")

    def test_issued_document_cannot_be_deleted(self):
        document = self._draft_document()
        FinancialDocumentService.issue_document(document_id=document.id)
        document.refresh_from_db()

        with self.assertRaises(ValueError):
            document.delete()

        self.assertTrue(FinancialDocument.objects.filter(id=document.id).exists())

    def test_locked_document_cannot_be_deleted_or_content_edited(self):
        document = self._draft_document()
        FinancialDocumentService.issue_document(document_id=document.id)
        FinancialDocumentService.lock_document(document_id=document.id)
        document.refresh_from_db()

        with self.assertRaises(ValueError):
            document.delete()

        document.metadata = {"tampered": True}
        with self.assertRaises(ValueError):
            document.save(update_fields=["metadata"])
