"""
Notification — Module 09 foundation, extended by Module 21 for dispatch.

A row-per-notification-intent record created by domain event handlers.
Handlers only ever create PENDING rows (see apps.kernel.events.handlers) —
dispatch is a separate concern, driven by NotificationDispatchService.

Retry/backoff fields and status transitions mirror
apps.jobs.models.JobDefinition (itself mirroring EventOutbox): exponential
backoff on failure, dead-letter after max_retries.
"""

import uuid

from django.db import models
from django.utils import timezone

from apps.common.managers import TenantScopedManager


class NotificationChannel(models.TextChoices):
    SMS = "SMS", "SMS"
    EMAIL = "EMAIL", "Email"
    PUSH = "PUSH", "Push"
    IN_APP = "IN_APP", "In-App"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DISPATCHING = "DISPATCHING", "Dispatching"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    DEAD_LETTER = "DEAD_LETTER", "Dead Letter"


class Notification(models.Model):
    """A single notification intent, created only by domain event handlers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    recipient = models.UUIDField(help_text="ID of the Person being notified.")
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    status = models.CharField(
        max_length=15,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    next_attempt_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Next time the dispatcher should attempt delivery.",
    )

    objects = TenantScopedManager()

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "recipient", "status"], name="idx_notif_tenant_recip_st"),
            models.Index(fields=["status", "next_attempt_at"], name="idx_notif_due"),
        ]

    def __str__(self):
        return f"Notification({self.channel}, {self.recipient}) [{self.status}]"

    def mark_dispatching(self):
        self.status = NotificationStatus.DISPATCHING
        self.save(update_fields=["status"])

    def mark_sent(self):
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at"])

    def mark_failed(self, error: str):
        """Mark this attempt as failed; schedule retry or dead-letter."""
        self.retry_count += 1
        self.failure_reason = error[:2000]
        if self.retry_count >= self.max_retries:
            self.status = NotificationStatus.DEAD_LETTER
        else:
            self.status = NotificationStatus.PENDING
            backoff_seconds = 2**self.retry_count
            self.next_attempt_at = timezone.now() + timezone.timedelta(seconds=backoff_seconds)
        self.save(update_fields=["status", "retry_count", "failure_reason", "next_attempt_at"])


class NotificationDeliveryAttempt(models.Model):
    """Append-only audit trail: one row per dispatch attempt of a Notification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="delivery_attempts")
    attempt_number = models.IntegerField()
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    provider_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=NotificationStatus.choices, db_index=True)
    attempted_at = models.DateTimeField(default=timezone.now)
    error_message = models.TextField(blank=True)
    response_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notifications_delivery_attempt"
        ordering = ["-attempted_at"]
        indexes = [
            models.Index(fields=["notification", "attempted_at"], name="idx_notif_attempt_notif"),
        ]

    def __str__(self):
        return f"DeliveryAttempt(notification={self.notification_id}, attempt={self.attempt_number}) [{self.status}]"
