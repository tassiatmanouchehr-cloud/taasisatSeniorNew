"""
Tests proving AssignmentService.assign() publishes an OrderAssigned domain
event after the SupplierAssignment is successfully persisted (and only then).
"""

import uuid

from apps.accounts.models.profiles import CustomerProfile
from apps.booking.services.assignment_service import AssignmentError, AssignmentService
from apps.kernel.events.base import ORDER_ASSIGNED
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.notifications.models import Notification, NotificationChannel

from .helpers import BookingTestCase


class AssignmentDomainEventTest(BookingTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = self._create_supplier()
        self.customer_profile = self._create_customer()
        self.order.customer_profile = self.customer_profile
        self.order.save(update_fields=["customer_profile"])

    def _create_customer(self) -> CustomerProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Test Customer")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name="Test Customer")

    def test_assign_publishes_order_assigned(self):
        with self.captureOnCommitCallbacks(execute=True):
            AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_ASSIGNED}").exists(),
        )
        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.channel, NotificationChannel.IN_APP)
        self.assertEqual(notification.recipient, self.customer_profile.person_id)

    def test_event_is_not_published_until_commit(self):
        AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_ASSIGNED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)

    def test_failed_assign_does_not_publish_an_event(self):
        other_tenant_supplier = self._create_supplier(tenant=self.other_tenant)

        with self.captureOnCommitCallbacks(execute=True), self.assertRaises(AssignmentError):
            AssignmentService.assign(order_id=self.order.id, supplier=other_tenant_supplier)

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=f"domain_event.{ORDER_ASSIGNED}").exists(),
        )
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)
