"""
Tests for the Module 09 notification handlers — both calling the handler
functions directly, and end-to-end through apps.kernel.events.publish()
using the handlers actually registered by NotificationsConfig.ready().
"""

import uuid

from django.test import TestCase

from apps.kernel.events.base import (
    INVOICE_ISSUED,
    ORDER_ASSIGNED,
    ORDER_COMPLETED,
    ORDER_CREATED,
    ORDER_STARTED,
    DomainEvent,
)
from apps.kernel.events.handlers import (
    handle_invoice_issued,
    handle_order_assigned,
    handle_order_completed,
    handle_order_created,
    handle_order_started,
)
from apps.kernel.events.publisher import publish
from apps.kernel.models import Tenant
from apps.notifications.models import Notification, NotificationChannel, NotificationStatus


class NotificationHandlersDirectTest(TestCase):
    """Calling each handler function directly with a DomainEvent."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"handler-{uuid.uuid4().hex[:8]}", name="Handler Test Tenant")
        self.recipient_id = uuid.uuid4()
        self.aggregate_id = uuid.uuid4()

    def _event(self, event_type, **payload_extra):
        payload = {"recipient_id": str(self.recipient_id), **payload_extra}
        return DomainEvent(
            event_type=event_type,
            tenant_id=self.tenant.id,
            aggregate_type="Order",
            aggregate_id=self.aggregate_id,
            payload=payload,
        )

    def test_handle_order_created_creates_in_app_notification(self):
        handle_order_created(self._event(ORDER_CREATED))

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(str(notification.recipient), str(self.recipient_id))
        self.assertEqual(notification.channel, NotificationChannel.IN_APP)
        self.assertEqual(notification.status, NotificationStatus.PENDING)
        self.assertIn(str(self.aggregate_id), notification.body)

    def test_handle_order_assigned_creates_in_app_notification(self):
        handle_order_assigned(self._event(ORDER_ASSIGNED))

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.channel, NotificationChannel.IN_APP)
        self.assertEqual(notification.subject, "Order Assigned")

    def test_handle_order_started_creates_in_app_notification(self):
        handle_order_started(self._event(ORDER_STARTED))

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.channel, NotificationChannel.IN_APP)
        self.assertEqual(notification.subject, "Order Started")

    def test_handle_order_completed_creates_in_app_notification(self):
        handle_order_completed(self._event(ORDER_COMPLETED))

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.channel, NotificationChannel.IN_APP)
        self.assertEqual(notification.subject, "Order Completed")

    def test_handle_invoice_issued_creates_email_notification(self):
        handle_invoice_issued(self._event(INVOICE_ISSUED))

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.channel, NotificationChannel.EMAIL)
        self.assertEqual(notification.subject, "Invoice Issued")

    def test_handler_falls_back_to_actor_id_when_no_recipient_in_payload(self):
        actor_id = uuid.uuid4()
        event = DomainEvent(
            event_type=ORDER_CREATED,
            tenant_id=self.tenant.id,
            aggregate_type="Order",
            aggregate_id=self.aggregate_id,
            payload={},
            actor_id=actor_id,
        )
        handle_order_created(event)

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.recipient, actor_id)

    def test_handler_skips_silently_when_no_recipient_available(self):
        event = DomainEvent(
            event_type=ORDER_CREATED,
            tenant_id=self.tenant.id,
            aggregate_type="Order",
            aggregate_id=self.aggregate_id,
            payload={},
        )
        handle_order_created(event)  # must not raise

        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)

    def test_handler_stores_full_payload_on_notification(self):
        handle_order_created(self._event(ORDER_CREATED, order_number="ORD-42"))

        notification = Notification.objects.get(tenant=self.tenant)
        self.assertEqual(notification.payload["order_number"], "ORD-42")

    def test_handler_respects_tenant_isolation(self):
        other_tenant = Tenant.objects.create(slug=f"handler-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        event = DomainEvent(
            event_type=ORDER_CREATED,
            tenant_id=other_tenant.id,
            aggregate_type="Order",
            aggregate_id=self.aggregate_id,
            payload={"recipient_id": str(self.recipient_id)},
        )
        handle_order_created(event)

        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)
        self.assertEqual(Notification.objects.filter(tenant=other_tenant).count(), 1)


class NotificationHandlersEndToEndTest(TestCase):
    """publish() using the real handlers registered by NotificationsConfig.ready()."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"e2e-{uuid.uuid4().hex[:8]}", name="E2E Test Tenant")
        self.recipient_id = uuid.uuid4()

    def _publish(self, event_type):
        event = DomainEvent(
            event_type=event_type,
            tenant_id=self.tenant.id,
            aggregate_type="Order",
            aggregate_id=uuid.uuid4(),
            payload={"recipient_id": str(self.recipient_id)},
        )
        publish(event)

    def test_publish_order_created_creates_notification_via_real_registration(self):
        self._publish(ORDER_CREATED)
        self.assertEqual(Notification.objects.filter(tenant=self.tenant, channel=NotificationChannel.IN_APP).count(), 1)

    def test_publish_invoice_issued_creates_email_notification_via_real_registration(self):
        self._publish(INVOICE_ISSUED)
        self.assertEqual(Notification.objects.filter(tenant=self.tenant, channel=NotificationChannel.EMAIL).count(), 1)

    def test_publish_unknown_event_type_creates_no_notification(self):
        event = DomainEvent(
            event_type="SomeUnhandledEvent",
            tenant_id=self.tenant.id,
            aggregate_type="Order",
            aggregate_id=uuid.uuid4(),
            payload={},
        )
        publish(event)  # must not raise
        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 0)

    def test_publish_all_five_event_types_each_create_one_notification(self):
        for event_type in (ORDER_CREATED, ORDER_ASSIGNED, ORDER_STARTED, ORDER_COMPLETED, INVOICE_ISSUED):
            self._publish(event_type)

        self.assertEqual(Notification.objects.filter(tenant=self.tenant).count(), 5)
