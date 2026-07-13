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

from .base import (
    DISPUTE_OPENED,
    DISPUTE_RESOLVED,
    INVOICE_ISSUED,
    OBJECTION_APPROVED_BY_CUSTOMER,
    OBJECTION_AUTO_APPROVED,
    OBJECTION_PERIOD_OPENED,
    ORDER_ASSIGNED,
    ORDER_COMPLETED,
    ORDER_CREATED,
    ORDER_STARTED,
    PAYMENT_HELD_IN_ESCROW,
    REFUND_INSTRUCTION_COMPLETED,
    REFUND_INSTRUCTION_FAILED,
    REFUND_INSTRUCTION_INITIATED,
    RELEASE_INSTRUCTION_CREATED,
    DomainEvent,
)
from .registry import EventRegistry

logger = logging.getLogger(__name__)


def _create_notification(event: DomainEvent, *, channel: str, subject: str, body: str) -> None:
    recipient = event.payload.get("recipient_id") or event.actor_id
    if recipient is None:
        logger.warning(
            "No recipient_id in payload and no actor_id for event_type=%s (event_id=%s); skipping notification.",
            event.event_type,
            event.id,
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
        event,
        channel=NotificationChannel.IN_APP,
        subject="Order Created",
        body=f"Your order {event.aggregate_id} has been created.",
    )


def handle_order_assigned(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Order Assigned",
        body=f"A provider has been assigned to order {event.aggregate_id}.",
    )


def handle_order_started(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Order Started",
        body=f"Work has started on order {event.aggregate_id}.",
    )


def handle_order_completed(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Order Completed",
        body=f"Order {event.aggregate_id} has been completed.",
    )


def handle_invoice_issued(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.EMAIL,
        subject="Invoice Issued",
        body=f"Invoice {event.aggregate_id} has been issued.",
    )


def handle_payment_held_in_escrow(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Payment Held",
        body=f"Your payment for order {event.aggregate_id} has been received and is held securely.",
    )


def handle_objection_period_opened(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Service Completed — Review Required",
        body=(
            f"Order {event.aggregate_id} is marked completed. Please review and approve, or open a "
            "dispute, before the objection period ends."
        ),
    )


def handle_objection_approved_by_customer(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Completion Approved",
        body=f"You approved completion of order {event.aggregate_id}.",
    )


def handle_objection_auto_approved(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Completion Auto-Approved",
        body=f"Order {event.aggregate_id} was automatically approved after the objection period ended.",
    )


def handle_dispute_opened(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Dispute Opened",
        body=f"A dispute was opened for order {event.aggregate_id}.",
    )


def handle_dispute_resolved(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Dispute Resolved",
        body=f"The dispute for order {event.aggregate_id} has been resolved.",
    )


def handle_release_instruction_created(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Amount Released",
        body=f"An amount held for order {event.aggregate_id} has been released.",
    )


def handle_refund_instruction_initiated(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Refund Initiated",
        body=f"A refund for order {event.aggregate_id} has been initiated.",
    )


def handle_refund_instruction_completed(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Refund Completed",
        body=f"Your refund for order {event.aggregate_id} has been completed.",
    )


def handle_refund_instruction_failed(event: DomainEvent) -> None:
    _create_notification(
        event,
        channel=NotificationChannel.IN_APP,
        subject="Refund Failed",
        body=f"Your refund for order {event.aggregate_id} could not be completed and requires review.",
    )


def register_handlers() -> None:
    """Idempotently register all Module 09 notification handlers."""
    EventRegistry.register(ORDER_CREATED, handle_order_created)
    EventRegistry.register(ORDER_ASSIGNED, handle_order_assigned)
    EventRegistry.register(ORDER_STARTED, handle_order_started)
    EventRegistry.register(ORDER_COMPLETED, handle_order_completed)
    EventRegistry.register(INVOICE_ISSUED, handle_invoice_issued)

    # Financial Core PR-B (Section 23).
    EventRegistry.register(PAYMENT_HELD_IN_ESCROW, handle_payment_held_in_escrow)
    EventRegistry.register(OBJECTION_PERIOD_OPENED, handle_objection_period_opened)
    EventRegistry.register(OBJECTION_APPROVED_BY_CUSTOMER, handle_objection_approved_by_customer)
    EventRegistry.register(OBJECTION_AUTO_APPROVED, handle_objection_auto_approved)
    EventRegistry.register(DISPUTE_OPENED, handle_dispute_opened)
    EventRegistry.register(DISPUTE_RESOLVED, handle_dispute_resolved)
    EventRegistry.register(RELEASE_INSTRUCTION_CREATED, handle_release_instruction_created)
    EventRegistry.register(REFUND_INSTRUCTION_INITIATED, handle_refund_instruction_initiated)
    EventRegistry.register(REFUND_INSTRUCTION_COMPLETED, handle_refund_instruction_completed)
    EventRegistry.register(REFUND_INSTRUCTION_FAILED, handle_refund_instruction_failed)
