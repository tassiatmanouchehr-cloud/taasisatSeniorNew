"""
ObjectionPeriod — Financial Core PR-B.

Starts when the canonical Execution/Completion engine
(apps.execution.services.session_service.ExecutionService.close_session())
completes a service whose payment is HELD in Escrow. The customer may
explicitly approve completion, open a dispute, or (if the configured
duration elapses with no action) be auto-approved by a scheduled job. Only
one ObjectionPeriod is ever OPEN for a given order at a time; a
reassignment/new-execution-cycle order gets its own fresh one (matching
CommissionSnapshot/PaymentDeadline's own FK-not-OneToOne precedent for the
same reason — see those models' docstrings).
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager


class ObjectionPeriodStatus(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Not Started"
    OPEN = "OPEN", "Open"
    CUSTOMER_APPROVED = "CUSTOMER_APPROVED", "Customer Approved"
    AUTO_APPROVED = "AUTO_APPROVED", "Auto Approved"
    DISPUTED = "DISPUTED", "Disputed"
    CLOSED = "CLOSED", "Closed"


class ApprovalSource(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Customer"
    AUTO = "AUTO", "Auto"


OPEN_OBJECTION_STATUSES = (ObjectionPeriodStatus.OPEN, ObjectionPeriodStatus.DISPUTED)


class ObjectionPeriod(models.Model):
    """One completion-review window for one execution cycle of one order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="objection_periods",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="objection_periods",
    )
    execution_session = models.ForeignKey(
        "execution.ExecutionSession",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="objection_periods",
    )
    escrow = models.ForeignKey(
        "finance.EscrowRecord",
        on_delete=models.PROTECT,
        related_name="objection_periods",
    )

    status = models.CharField(
        max_length=20,
        choices=ObjectionPeriodStatus.choices,
        default=ObjectionPeriodStatus.NOT_STARTED,
        db_index=True,
    )

    completion_at = models.DateTimeField()
    objection_deadline = models.DateTimeField()

    customer_approved_at = models.DateTimeField(null=True, blank=True)
    auto_approved_at = models.DateTimeField(null=True, blank=True)
    approval_source = models.CharField(max_length=20, choices=ApprovalSource.choices, blank=True)

    auto_approve_job_id = models.UUIDField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_objection_period"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_objperiod_tenant_ord_st"),
        ]

    def __str__(self):
        return f"ObjectionPeriod(order={self.order_id}) [{self.status}]"


class ObjectionPeriodExtension(models.Model):
    """Append-only extension history — mirrors
    apps.commission.models.deadline.PaymentDeadlineExtension exactly."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="objection_period_extensions",
    )
    objection_period = models.ForeignKey(
        "commission.ObjectionPeriod",
        on_delete=models.CASCADE,
        related_name="extensions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="objection_period_extensions",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    old_deadline_at = models.DateTimeField()
    new_deadline_at = models.DateTimeField()
    reason = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_objection_period_extension"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ObjectionPeriodExtension({self.objection_period_id}) -> {self.new_deadline_at}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("ObjectionPeriodExtension is append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("ObjectionPeriodExtension cannot be deleted.")
