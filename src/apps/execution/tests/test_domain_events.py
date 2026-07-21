"""
Tests proving ExecutionService publishes OrderStarted (start_session) and
OrderCompleted (close_session) domain events after the respective state
change is successfully persisted (and only then).
"""

import uuid

from apps.accounts.models.profiles import CustomerProfile
from apps.execution.models import ExecutionSessionStatus
from apps.execution.services.session_service import ExecutionError, ExecutionService
from apps.kernel.events.base import ORDER_COMPLETED, ORDER_STARTED
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.notifications.models import Notification, NotificationChannel

from .helpers import ExecutionTestCase


class ExecutionDomainEventTest(ExecutionTestCase):
    def setUp(self):
        super().setUp()
        self.customer_profile = self._create_customer()
        self.order.customer_profile = self.customer_profile
        self.order.save(update_fields=["customer_profile"])

    def _create_customer(self) -> CustomerProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Test Customer")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name="Test Customer")

    def test_start_session_publishes_order_started(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

        with self.captureOnCommitCallbacks(execute=True):
            ExecutionService.start_session(session_id=session.id)

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_STARTED}").exists(),
        )
        notification = Notification.objects.get(tenant=self.tenant, channel=NotificationChannel.IN_APP)
        self.assertEqual(notification.recipient, self.customer_profile.person_id)
        self.assertEqual(notification.subject, "Order Started")

    def test_close_session_publishes_order_completed(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)

        with self.captureOnCommitCallbacks(execute=True):
            ExecutionService.close_session(session_id=session.id)

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_COMPLETED}").exists(),
        )
        notification = Notification.objects.get(tenant=self.tenant, subject="Order Completed")
        self.assertEqual(notification.recipient, self.customer_profile.person_id)

    def test_complete_session_does_not_publish_order_completed(self):
        """complete_session() only reaches PROVIDER_COMPLETED — the Order itself isn't
        completed yet, so OrderCompleted must not fire until close_session()."""
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=session.id)

        with self.captureOnCommitCallbacks(execute=True):
            ExecutionService.complete_session(session_id=session.id)

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_COMPLETED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)

    def test_event_is_not_published_until_commit(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        ExecutionService.start_session(session_id=session.id)

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_STARTED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)

    def test_failed_start_session_does_not_publish_an_event(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)

        with self.captureOnCommitCallbacks(execute=True):
            ExecutionService.start_session(session_id=session.id)  # succeeds -> publishes once

        self.assertEqual(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_STARTED}").count(),
            1,
        )

        with self.captureOnCommitCallbacks(execute=True), self.assertRaises(ExecutionError):
            ExecutionService.start_session(session_id=session.id)  # already started -> must fail, no new event

        self.assertEqual(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_STARTED}").count(),
            1,
        )

    def test_failed_close_session_does_not_publish_an_event(self):
        session = ExecutionService.create_session(supplier_assignment=self.supplier_assignment)
        # Session is still SCHEDULED — close_session() requires PROVIDER_COMPLETED/CUSTOMER_PENDING.
        self.assertEqual(session.status, ExecutionSessionStatus.SCHEDULED)

        with self.captureOnCommitCallbacks(execute=True), self.assertRaises(ExecutionError):
            ExecutionService.close_session(session_id=session.id)

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_COMPLETED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)
