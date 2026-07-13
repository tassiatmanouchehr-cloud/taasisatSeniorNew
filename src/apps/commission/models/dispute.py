"""
Dispute / DisputeLine / DisputeResolution — Financial Core PR-B.

A Dispute represents an exact disputed monetary amount against a held
Escrow, optionally broken down into DisputeLine allocations against
specific FinancialDocumentItem rows. DisputeResolution is the immutable,
append-only record of how a platform-authorized actor allocated the
disputed (blocked) amount once resolved — customer refund, and/or
platform/company/caregiver release, conserving the blocked amount exactly.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager


class DisputeStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED", "Partially Resolved"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


OPEN_DISPUTE_STATUSES = (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW, DisputeStatus.PARTIALLY_RESOLVED)
TERMINAL_DISPUTE_STATUSES = (DisputeStatus.RESOLVED, DisputeStatus.REJECTED, DisputeStatus.CANCELLED)


class DisputeReasonCode(models.TextChoices):
    SERVICE_NOT_PERFORMED = "SERVICE_NOT_PERFORMED", "Service Not Performed"
    SERVICE_QUALITY = "SERVICE_QUALITY", "Service Quality"
    INCORRECT_AMOUNT = "INCORRECT_AMOUNT", "Incorrect Amount"
    DURATION_MISMATCH = "DURATION_MISMATCH", "Duration Mismatch"
    UNAUTHORIZED_EXTRA_CHARGE = "UNAUTHORIZED_EXTRA_CHARGE", "Unauthorized Extra Charge"
    OTHER = "OTHER", "Other"


class Dispute(models.Model):
    """One customer-raised dispute against an exact amount of a held Escrow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="disputes",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="disputes",
    )
    invoice = models.ForeignKey(
        "finance.FinancialDocument",
        on_delete=models.PROTECT,
        related_name="disputes",
    )
    escrow = models.ForeignKey(
        "finance.EscrowRecord",
        on_delete=models.PROTECT,
        related_name="disputes",
    )
    customer_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="disputes_as_customer",
    )
    supplier_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="disputes_as_supplier",
    )

    disputed_amount_irr = models.PositiveBigIntegerField()
    reason_code = models.CharField(max_length=40, choices=DisputeReasonCode.choices)
    description = models.TextField(blank=True)
    evidence_metadata = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=DisputeStatus.choices, default=DisputeStatus.OPEN, db_index=True)
    resolution_type = models.CharField(max_length=40, blank=True)

    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes_opened",
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    correlation_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_dispute"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_dispute_tenant_ord_st"),
            models.Index(fields=["tenant", "escrow", "status"], name="idx_dispute_tenant_esc_st"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_dispute_tenant_idempotency",
            ),
            models.CheckConstraint(check=models.Q(disputed_amount_irr__gt=0), name="chk_dispute_amount_positive"),
        ]

    def __str__(self):
        return f"Dispute({self.disputed_amount_irr} IRR, order={self.order_id}) [{self.status}]"


class DisputeLine(models.Model):
    """One invoice-item-linked allocation of a Dispute's disputed amount."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="dispute_lines",
    )
    dispute = models.ForeignKey(
        "commission.Dispute",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    invoice_item = models.ForeignKey(
        "finance.FinancialDocumentItem",
        on_delete=models.PROTECT,
        related_name="dispute_lines",
    )

    disputed_amount_irr = models.PositiveBigIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    evidence_reference = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_dispute_line"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(disputed_amount_irr__gt=0), name="chk_disputeline_amount_positive"),
        ]

    def __str__(self):
        return f"DisputeLine({self.disputed_amount_irr} IRR) on {self.invoice_item_id}"


class DisputeResolution(models.Model):
    """Immutable, append-only record of one dispute-resolution decision.

    total_blocked_amount_irr must equal the sum of the four allocation
    fields exactly (enforced at the database level) — the resolution
    conserves the blocked amount, it never creates or destroys money."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="dispute_resolutions",
    )
    dispute = models.ForeignKey(
        "commission.Dispute",
        on_delete=models.PROTECT,
        related_name="resolutions",
    )
    commission_snapshot = models.ForeignKey(
        "commission.CommissionSnapshot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dispute_resolutions",
    )

    total_blocked_amount_irr = models.PositiveBigIntegerField()
    customer_refund_amount_irr = models.PositiveBigIntegerField(default=0)
    platform_amount_irr = models.PositiveBigIntegerField(default=0)
    company_amount_irr = models.PositiveBigIntegerField(default=0)
    caregiver_amount_irr = models.PositiveBigIntegerField(default=0)

    reason = models.TextField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    resolved_at = models.DateTimeField(auto_now_add=True)

    correlation_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_dispute_resolution"
        ordering = ["-resolved_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_disputeres_tenant_idempotency",
            ),
            models.CheckConstraint(
                check=models.Q(
                    total_blocked_amount_irr=(
                        models.F("customer_refund_amount_irr")
                        + models.F("platform_amount_irr")
                        + models.F("company_amount_irr")
                        + models.F("caregiver_amount_irr")
                    ),
                ),
                name="chk_disputeres_conservation",
            ),
        ]

    def __str__(self):
        return f"DisputeResolution({self.dispute_id}, {self.total_blocked_amount_irr} IRR)"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("DisputeResolution is append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("DisputeResolution cannot be deleted.")
