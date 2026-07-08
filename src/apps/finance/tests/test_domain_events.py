"""
Tests proving FinancialDocumentService.issue_document() publishes an
InvoiceIssued domain event after the document is successfully persisted
(and only then).
"""

from apps.finance.services import FinanceError, FinancialDocumentService
from apps.kernel.events.base import INVOICE_ISSUED
from apps.kernel.models.audit import AuditLog
from apps.notifications.models import Notification, NotificationChannel

from .helpers import FinanceTestCase


class InvoiceDomainEventTest(FinanceTestCase):
    def _draft_document(self):
        session = self._close_execution_session()
        return FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id, items=self._invoice_items(),
        )

    def test_issue_document_publishes_invoice_issued(self):
        document = self._draft_document()

        with self.captureOnCommitCallbacks(execute=True):
            FinancialDocumentService.issue_document(document_id=document.id)

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{INVOICE_ISSUED}").exists(),
        )
        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.channel, NotificationChannel.EMAIL)
        self.assertEqual(notification.recipient, self.customer_profile.person_id)
        self.assertEqual(notification.payload["total_amount"], str(document.total_amount))

    def test_event_is_not_published_until_commit(self):
        document = self._draft_document()

        FinancialDocumentService.issue_document(document_id=document.id)

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{INVOICE_ISSUED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)

    def test_failed_issue_document_does_not_publish_an_event(self):
        document = self._draft_document()
        FinancialDocumentService.issue_document(document_id=document.id)  # now ISSUED

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(FinanceError):
                FinancialDocumentService.issue_document(document_id=document.id)  # already issued -> must fail

        self.assertEqual(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{INVOICE_ISSUED}").count(), 0,
        )
