"""
PaymentDeadline / PaymentDeadlineExtension — Financial Core PR-A.

Represents the configurable payment-completion window opened when a
proposal/offer is accepted (apps.booking.services.assignment_service
.AssignmentService.assign() — the existing accepted-proposal representation;
no new Offer model was introduced, per the explicit instruction to map the
current representation first).

One PENDING PaymentDeadline exists per order at a time; each expiry cycle
(the customer fails to pay in time, the assignment expires, the order
reopens, gets a new supplier) creates a fresh PaymentDeadline row rather
than reusing one — this preserves a full audit trail of every payment
window an order ever had, instead of overwriting history.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager


class PaymentDeadlineStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentDeadline(models.Model):
    """One payment-completion window for one order (one assignment cycle)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="payment_deadlines",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payment_deadlines",
    )
    assignment = models.ForeignKey(
        "booking.SupplierAssignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_deadlines",
    )

    original_deadline_at = models.DateTimeField()
    deadline_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=PaymentDeadlineStatus.choices,
        default=PaymentDeadlineStatus.PENDING,
        db_index=True,
    )

    expiry_job_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="apps.jobs.models.JobDefinition.id for the scheduled expiry sweep, so extensions can reschedule it.",
    )

    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_payment_deadline"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_paydeadline_ord_st"),
            models.Index(fields=["status", "deadline_at"], name="idx_paydeadline_status_due"),
        ]

    def __str__(self):
        return f"PaymentDeadline(order={self.order_id}) due {self.deadline_at} [{self.status}]"


class PaymentDeadlineExtension(models.Model):
    """Append-only audit trail of every deadline extension."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="payment_deadline_extensions",
    )
    deadline = models.ForeignKey(
        PaymentDeadline,
        on_delete=models.CASCADE,
        related_name="extensions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payment_deadline_extensions",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_deadline_extensions",
    )
    old_deadline_at = models.DateTimeField()
    new_deadline_at = models.DateTimeField()
    reason = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_payment_deadline_extension"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PaymentDeadlineExtension(deadline={self.deadline_id}) {self.old_deadline_at} -> {self.new_deadline_at}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("PaymentDeadlineExtension is append-only and cannot be modified after creation.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("PaymentDeadlineExtension cannot be deleted.")
