"""
Audit Log model.

Append-only audit records following the Module 25 Audit Envelope Standard.
Audit records are NEVER updated or deleted — corrections are new entries.

Every material change to contracts, policies, permissions, configuration,
financial data, and security-sensitive state must be audited.

References:
- ADR-001.21 (Financial ledger append-only — same principle for audit)
- Module 25: 09_Observability_Audit/Audit_Envelope_Standard.md
- Phase 0.5 Deliverable 14 (AuditLog owned by M25, audit_class=compliance)
- Phase 0.5 Deliverable 17 (Partitioning strategy: monthly by occurred_at)
"""

import uuid

from django.db import models
from django.utils import timezone


class AuditClassification(models.TextChoices):
    """Audit classification per Module 25 Audit Envelope."""

    STANDARD = "standard", "Standard"
    FINANCIAL = "financial", "Financial"
    SECURITY = "security", "Security"
    COMPLIANCE = "compliance", "Compliance"


class AuditLog(models.Model):
    """
    Append-only audit record.

    Once created, an AuditLog record is NEVER modified or deleted.
    It captures: who did what, to which resource, when, why, and what changed.

    Sensitive values must be hashed, redacted, or referenced securely —
    never stored raw in the audit record (per Module 25 spec).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    # When
    occurred_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the audited action occurred.",
    )

    # Who
    actor_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Person who performed the action.",
    )
    actor_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Actor type: 'person', 'system', 'integration'.",
    )
    actor_display = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable actor name (for display, not identity).",
    )
    impersonator_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="If impersonating, the real actor's ID.",
    )

    # What
    action = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Action performed, e.g., 'policy.publish', 'role.assign'.",
    )
    module_id = models.CharField(
        max_length=10,
        help_text="Module that owns this action, e.g., 'M08'.",
    )

    # On which resource
    resource_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Type of affected resource, e.g., 'Role', 'Tenant'.",
    )
    resource_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the affected resource.",
    )

    # Change details (hashed/redacted for sensitive data)
    before_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="State before the change (redacted/hashed for sensitive fields).",
    )
    after_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="State after the change (redacted/hashed for sensitive fields).",
    )

    # Why
    reason = models.TextField(
        blank=True,
        help_text="Human-provided reason for the action (optional).",
    )

    # Tracing
    correlation_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Links to originating request/event chain.",
    )

    # Context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address (if from HTTP request).",
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        help_text="Client user agent (truncated).",
    )

    # Classification
    audit_class = models.CharField(
        max_length=20,
        choices=AuditClassification.choices,
        default=AuditClassification.STANDARD,
        db_index=True,
    )
    retention_policy = models.CharField(
        max_length=50,
        default="standard",
        help_text="Retention policy identifier for archival.",
    )

    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured context for this audit entry.",
    )

    class Meta:
        db_table = 'kernel"."audit_log'
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Log Entries"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "occurred_at"],
                name="idx_audit_tenant_time",
            ),
            models.Index(
                fields=["actor_id", "occurred_at"],
                name="idx_audit_actor_time",
            ),
            models.Index(
                fields=["resource_type", "resource_id"],
                name="idx_audit_resource",
            ),
            models.Index(
                fields=["action", "occurred_at"],
                name="idx_audit_action_time",
            ),
        ]

    def __str__(self):
        return f"[{self.occurred_at:%Y-%m-%d %H:%M}] {self.action} on {self.resource_type}"

    def save(self, *args, **kwargs):
        """Enforce append-only: prevent updates to existing records."""
        if not self._state.adding:
            raise ValueError(
                "AuditLog records are immutable. Cannot update an existing audit entry. "
                "Create a new correction/addendum record instead."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of audit records."""
        raise ValueError("AuditLog records cannot be deleted. They are append-only.")
