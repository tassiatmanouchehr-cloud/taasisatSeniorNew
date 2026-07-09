"""
NotificationQueryService — Customer Experience Phase 1 remediation.

Centralizes the recipient-scoped Notification reads apps.portal needs, so
views never call the ORM directly (ADR-007's thin-controller rule) and
never duplicate the NotificationStatus.PENDING literal.
"""


class NotificationQueryService:
    """Read-only Notification lookups, always tenant- and recipient-scoped."""

    @classmethod
    def list_recent_for_recipient(cls, *, tenant_id, recipient_id, limit):
        from ..models import Notification

        return Notification.objects.for_tenant(tenant_id).filter(
            recipient=recipient_id,
        ).order_by("-created_at")[:limit]

    @classmethod
    def count_unread_for_recipient(cls, *, tenant_id, recipient_id):
        from ..models import Notification, NotificationStatus

        return Notification.objects.for_tenant(tenant_id).filter(
            recipient=recipient_id, status=NotificationStatus.PENDING,
        ).count()

    @classmethod
    def list_for_recipient(cls, *, tenant_id, recipient_id, only=None):
        """`only`: None (all), "unread", or "read"."""
        from ..models import Notification, NotificationStatus

        queryset = Notification.objects.for_tenant(tenant_id).filter(
            recipient=recipient_id,
        ).order_by("-created_at")

        if only == "unread":
            queryset = queryset.filter(status=NotificationStatus.PENDING)
        elif only == "read":
            queryset = queryset.exclude(status=NotificationStatus.PENDING)

        return queryset
