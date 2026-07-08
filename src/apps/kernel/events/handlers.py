"""
Notification event handlers — Module 09 foundation.

Handlers only ever create Notification rows (status=PENDING). Nothing is
delivered — that is explicitly out of scope for this sprint. Registration
is idempotent (see EventRegistry.register) and happens once, from
apps.notifications.apps.NotificationsConfig.ready() — this module is never
imported at kernel package load time (see apps/kernel/events/__init__.py),
which is what keeps this kernel -> notifications dependency from becoming
a circular import.
"""

import logging

from apps.notifications.models import Notification, NotificationChannel, NotificationStatus

from .base import INVOICE_ISSUED, ORDER_ASSIGNED, ORDER_COMPLETED, ORDER_CREATED, ORDER_STARTED, DomainEvent
from .registry import EventRegistry

logger = logging.getLogger(__name__)


def _create_notification(event: DomainEvent, *, channel: str, subject: str, body: str) -> None:
    recipient = event.payload.get("recipient_id") or event.actor_id
    if recipient is None:
        logger.warning(
            "No recipient_id in payload and no actor_id for event_type=%s (event_id=%s); skipping notification.",
            event.event_type, event.id,
        )
        return

    Notification.objects.create(
        tenant_id=event.tenant_id,
        recipient=recipient,
        channel=channel,
        status=NotificationStatus.PENDING,
        subject=subject,
        body=body,
        payload=event.payload,
    )


def handle_order_created(event: DomainEvent) -> None:
    _create_notification(
        event, channel=NotificationChannel.IN_APP,
        subject="Order Created",
        body=f"Your order {event.aggregate_id} has been created.",
    )


def handle_order_assigned(event: DomainEvent) -> None:
    _create_notification(
        event, channel=NotificationChannel.IN_APP,
        subject="Order Assigned",
        body=f"A provider has been assigned to order {event.aggregate_id}.",
    )


def handle_order_started(event: DomainEvent) -> None:
    _create_notification(
        event, channel=NotificationChannel.IN_APP,
        subject="Order Started",
        body=f"Work has started on order {event.aggregate_id}.",
    )


def handle_order_completed(event: DomainEvent) -> None:
    _create_notification(
        event, channel=NotificationChannel.IN_APP,
        subject="Order Completed",
        body=f"Order {event.aggregate_id} has been completed.",
    )


def handle_invoice_issued(event: DomainEvent) -> None:
    _create_notification(
        event, channel=NotificationChannel.EMAIL,
        subject="Invoice Issued",
        body=f"Invoice {event.aggregate_id} has been issued.",
    )


def register_handlers() -> None:
    """Idempotently register all Module 09 notification handlers."""
    EventRegistry.register(ORDER_CREATED, handle_order_created)
    EventRegistry.register(ORDER_ASSIGNED, handle_order_assigned)
    EventRegistry.register(ORDER_STARTED, handle_order_started)
    EventRegistry.register(ORDER_COMPLETED, handle_order_completed)
    EventRegistry.register(INVOICE_ISSUED, handle_invoice_issued)
