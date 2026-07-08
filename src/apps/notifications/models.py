"""
Notification — Module 09 foundation.

A row-per-notification-intent record created by domain event handlers.
No provider integration: nothing here actually sends an SMS/email/push —
delivery is explicitly out of scope for this sprint. Handlers only ever
create PENDING rows; SENT/FAILED are reserved for a future delivery layer.
"""

import uuid

from django.db import models

from apps.common.managers import TenantScopedManager


class NotificationChannel(models.TextChoices):
    SMS = "SMS", "SMS"
    EMAIL = "EMAIL", "Email"
    PUSH = "PUSH", "Push"
    IN_APP = "IN_APP", "In-App"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class Notification(models.Model):
    """A single notification intent, created only by domain event handlers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="notifications",
    )
    recipient = models.UUIDField(help_text="ID of the Person being notified.")
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    status = models.CharField(
        max_length=10, choices=NotificationStatus.choices, default=NotificationStatus.PENDING, db_index=True,
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "recipient", "status"], name="idx_notif_tenant_recip_st"),
        ]

    def __str__(self):
        return f"Notification({self.channel}, {self.recipient}) [{self.status}]"
