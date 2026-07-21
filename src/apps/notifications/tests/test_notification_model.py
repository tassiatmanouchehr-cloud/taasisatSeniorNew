"""Tests for the Notification model — Module 09 foundation."""

import uuid

from django.test import TestCase

from apps.kernel.models import Tenant
from apps.notifications.models import Notification, NotificationChannel, NotificationStatus


class NotificationModelTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"notif-{uuid.uuid4().hex[:8]}", name="Notification Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"notif-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

    def test_create_with_minimal_fields_defaults_to_pending(self):
        notification = Notification.objects.create(
            tenant=self.tenant,
            recipient=uuid.uuid4(),
            channel=NotificationChannel.SMS,
        )
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertIsNone(notification.sent_at)
        self.assertEqual(notification.failure_reason, "")
        self.assertEqual(notification.payload, {})

    def test_channel_choices_accept_all_four_values(self):
        for channel in (
            NotificationChannel.SMS,
            NotificationChannel.EMAIL,
            NotificationChannel.PUSH,
            NotificationChannel.IN_APP,
        ):
            notification = Notification.objects.create(tenant=self.tenant, recipient=uuid.uuid4(), channel=channel)
            self.assertEqual(notification.channel, channel)

    def test_status_can_be_set_to_sent_or_failed(self):
        notification = Notification.objects.create(
            tenant=self.tenant,
            recipient=uuid.uuid4(),
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.FAILED,
            failure_reason="provider unavailable",
        )
        self.assertEqual(notification.status, NotificationStatus.FAILED)
        self.assertEqual(notification.failure_reason, "provider unavailable")

    def test_for_tenant_scopes_notifications(self):
        Notification.objects.create(tenant=self.tenant, recipient=uuid.uuid4(), channel=NotificationChannel.IN_APP)

        self.assertEqual(Notification.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(Notification.objects.for_tenant(self.other_tenant.id).count(), 0)

    def test_payload_stores_arbitrary_json(self):
        notification = Notification.objects.create(
            tenant=self.tenant,
            recipient=uuid.uuid4(),
            channel=NotificationChannel.PUSH,
            payload={"order_id": "abc-123", "count": 3},
        )
        notification.refresh_from_db()
        self.assertEqual(notification.payload, {"order_id": "abc-123", "count": 3})
