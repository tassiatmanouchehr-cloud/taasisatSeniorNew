"""
CES Event Outbox model.

Implements the transactional outbox pattern for the Cross-Module Event System (CES).
Events are written to the outbox in the same database transaction as business state,
then published asynchronously by a background worker.

Every event conforms to the CES Kernel Envelope (Module 25):
- event_id, event_type, event_version, occurred_at, published_at
- tenant_id, source_module, actor
- correlation_id, causation_id, idempotency_key
- privacy_class, audit_class
- payload (domain-specific content)

References:
- ADR-001.14 (Business modules emit CES events only)
- ADR-001.15 (Configuration uses CCS)
- Module 25: 04_Event_Kernel/CES_Kernel_Envelope.md
- Phase 0.5 Deliverable 11 (Aggregate Boundaries — outbox co-transacts)
"""

import uuid

from django.db import models
from django.utils import timezone


class EventStatus(models.TextChoices):
    """Event outbox processing states."""

    PENDING = "pending", "Pending"
    PUBLISHED = "published", "Published"
    FAILED = "failed", "Failed"
    DEAD_LETTER = "dead_letter", "Dead Letter"


class PrivacyClass(models.TextChoices):
    """Event privacy classification per Module 25."""

    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    RESTRICTED = "restricted", "Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class AuditClass(models.TextChoices):
    """Event audit classification per Module 25."""

    NONE = "none", "None"
    STANDARD = "standard", "Standard"
    FINANCIAL = "financial", "Financial"
    SECURITY = "security", "Security"
    COMPLIANCE = "compliance", "Compliance"


class EventOutbox(models.Model):
    """
    Transactional event outbox.

    Events are written here in the same DB transaction as the business state change.
    A background worker (Celery task) polls pending events and dispatches them
    to consumers. Failed events are retried with backoff until max_retries,
    then moved to dead_letter status.

    This model directly implements the CES Kernel Envelope shape.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    # Event identity
    event_type = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Fully qualified event type, e.g., 'Request.Created.v1'",
    )
    event_version = models.CharField(max_length=10, default="1.0")

    # Timing
    occurred_at = models.DateTimeField(
        help_text="When the business event actually occurred (source of truth).",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the event was successfully dispatched to consumers.",
    )

    # Source
    source_module = models.CharField(
        max_length=10,
        help_text="Module that produced this event, e.g., 'M01'.",
    )
    source_entity_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the entity that changed.",
    )
    source_entity_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of the entity that changed, e.g., 'ServiceRequest'.",
    )

    # Actor
    actor_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Person/system that caused this event.",
    )
    actor_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of actor: 'person', 'system', 'integration'.",
    )

    # Tracing
    correlation_id = models.UUIDField(
        db_index=True,
        help_text="Links related events across a request chain.",
    )
    causation_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the event that directly caused this one.",
    )
    idempotency_key = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Prevents duplicate processing of the same business operation.",
    )

    # Classification
    privacy_class = models.CharField(
        max_length=20,
        choices=PrivacyClass.choices,
        default=PrivacyClass.INTERNAL,
    )
    audit_class = models.CharField(
        max_length=20,
        choices=AuditClass.choices,
        default=AuditClass.STANDARD,
    )

    # Schema reference
    schema_ref = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reference to the JSON schema for this event's payload.",
    )

    # Payload
    payload = models.JSONField(
        default=dict,
        help_text="Domain-specific event data. Must conform to schema_ref.",
    )

    # Processing state
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PENDING,
        db_index=True,
    )
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled time for next retry attempt.",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Last error encountered during publishing.",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'kernel"."event_outbox'
        verbose_name = "Event Outbox"
        verbose_name_plural = "Event Outbox Entries"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="idx_outbox_pending",
            ),
            models.Index(
                fields=["status", "next_retry_at"],
                name="idx_outbox_retry",
            ),
            models.Index(
                fields=["tenant_id", "event_type", "created_at"],
                name="idx_outbox_tenant_type",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} [{self.status}] ({self.id})"

    def mark_published(self):
        """Mark this event as successfully published."""
        self.status = EventStatus.PUBLISHED
        self.published_at = timezone.now()
        self.save(update_fields=["status", "published_at"])

    def mark_failed(self, error: str):
        """Mark this event as failed; schedule retry or dead-letter."""
        self.retry_count += 1
        self.error_message = error[:2000]  # Truncate to prevent bloat
        if self.retry_count >= self.max_retries:
            self.status = EventStatus.DEAD_LETTER
        else:
            self.status = EventStatus.FAILED
            # Exponential backoff: 2^retry_count seconds (2, 4, 8, 16, 32...)
            backoff_seconds = 2**self.retry_count
            self.next_retry_at = timezone.now() + timezone.timedelta(seconds=backoff_seconds)
        self.save(update_fields=["status", "retry_count", "error_message", "next_retry_at"])
