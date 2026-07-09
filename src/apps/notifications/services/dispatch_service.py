"""
NotificationDispatchService — Module 21 foundation.

The single execution path for turning a PENDING Notification into a SENT
(or retried/dead-lettered) one. Both the apps.jobs handler
(notifications.dispatch_pending) and the dispatch_notifications management
command call dispatch_pending() — neither re-implements this logic.

Locking: dispatch_pending() uses select_for_update(skip_locked=True) and
transitions each claimed Notification to DISPATCHING before releasing the
lock, so two concurrent dispatch runs never send the same notification
twice, and a Notification already SENT is never selected again — dispatch
is idempotent by construction.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.notifications.errors import NotificationsError
from apps.notifications.providers.registry import NotificationProviderRegistry

logger = logging.getLogger(__name__)


class NotificationDispatchService:
    """Selects and dispatches due, pending notifications."""

    @classmethod
    def _claim_due_notifications(cls, *, tenant_id, limit):
        from apps.notifications.models import Notification, NotificationStatus

        claimed = []
        with transaction.atomic():
            qs = Notification.objects.select_for_update(skip_locked=True).filter(
                status=NotificationStatus.PENDING,
                next_attempt_at__lte=timezone.now(),
            )
            if tenant_id is not None:
                qs = qs.filter(tenant_id=tenant_id)
            for notification in qs.order_by("next_attempt_at")[:limit]:
                notification.mark_dispatching()
                claimed.append(notification)
        return claimed

    @classmethod
    def dispatch_one(cls, notification):
        """Dispatch a single already-claimed (DISPATCHING) notification.
        Records a NotificationDeliveryAttempt and updates its status.
        Never raises — failures are captured and recorded on the
        notification/attempt instead."""
        from apps.notifications.models import NotificationDeliveryAttempt, NotificationStatus

        attempt = NotificationDeliveryAttempt.objects.create(
            notification=notification,
            attempt_number=notification.retry_count + 1,
            channel=notification.channel,
            status=NotificationStatus.DISPATCHING,
        )

        try:
            provider = NotificationProviderRegistry.get_provider(notification.channel)
        except NotificationsError as exc:
            notification.mark_failed(str(exc))
            attempt.status = notification.status
            attempt.error_message = str(exc)
            attempt.save(update_fields=["status", "error_message"])
            return notification

        attempt.provider_name = getattr(provider, "name", provider.__class__.__name__)
        result = provider.send(notification)

        if result.success:
            notification.mark_sent()
            attempt.status = NotificationStatus.SENT
            attempt.response_payload = {"external_id": result.external_id, "message": result.message}
            attempt.save(update_fields=["status", "provider_name", "response_payload"])
        else:
            notification.mark_failed(result.message)
            attempt.status = notification.status
            attempt.error_message = result.message
            attempt.save(update_fields=["status", "provider_name", "error_message"])

        return notification

    @classmethod
    def dispatch_pending(cls, *, tenant_id=None, limit: int = 100):
        """Claim and dispatch up to `limit` due PENDING notifications
        (optionally scoped to a single tenant). Returns the list of
        Notification instances that were processed."""
        claimed = cls._claim_due_notifications(tenant_id=tenant_id, limit=limit)
        for notification in claimed:
            cls.dispatch_one(notification)
        return claimed
