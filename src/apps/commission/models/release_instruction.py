"""
ReleaseInstruction — Financial Core PR-B.

The canonical, immutable record of "this exact amount of this Escrow is
now earmarked for release" — produced by customer approval, auto-
approval, an undisputed partial release, or a dispute resolution. PR-B
never credits a wallet from this; it only ever creates the instruction.
apps.commission.services.escrow_service consumes it by moving the same
amount from EscrowRecord.remaining_amount_irr into released_amount_irr
(see EscrowService.apply_release()) — the money is now "spoken for" even
though no beneficiary wallet exists yet. PR-C is the only future consumer
allowed to transition a ReleaseInstruction from READY to CONSUMED (and
perform the actual multi-party wallet credit using
apps.commission.services.allocation_calculator.AllocationCalculator against
the referenced commission_snapshot).
"""

import uuid

from django.db import models

from apps.common.managers import TenantScopedManager


class ReleaseInstructionSource(models.TextChoices):
    CUSTOMER_APPROVAL = "CUSTOMER_APPROVAL", "Customer Approval"
    AUTO_APPROVAL = "AUTO_APPROVAL", "Auto Approval"
    UNDISPUTED_PARTIAL = "UNDISPUTED_PARTIAL", "Undisputed Partial Release"
    DISPUTE_RESOLUTION = "DISPUTE_RESOLUTION", "Dispute Resolution"


class ReleaseInstructionStatus(models.TextChoices):
    PENDING_ALLOCATION = "PENDING_ALLOCATION", "Pending Allocation"
    READY = "READY", "Ready"
    CONSUMED = "CONSUMED", "Consumed"
    CANCELLED = "CANCELLED", "Cancelled"


class ReleaseInstruction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="release_instructions",
    )
    escrow = models.ForeignKey(
        "finance.EscrowRecord",
        on_delete=models.PROTECT,
        related_name="release_instructions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="release_instructions",
    )
    invoice = models.ForeignKey(
        "finance.FinancialDocument",
        on_delete=models.PROTECT,
        related_name="release_instructions",
    )
    commission_snapshot = models.ForeignKey(
        "commission.CommissionSnapshot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="release_instructions",
    )
    dispute_resolution = models.ForeignKey(
        "commission.DisputeResolution",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="release_instructions",
    )

    source = models.CharField(max_length=30, choices=ReleaseInstructionSource.choices)
    gross_releasable_amount_irr = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=10, default="IRR")
    status = models.CharField(
        max_length=20,
        choices=ReleaseInstructionStatus.choices,
        default=ReleaseInstructionStatus.READY,
        db_index=True,
    )

    correlation_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_release_instruction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "escrow", "status"], name="idx_relinstr_tenant_esc_st"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_relinstr_tenant_idempotency",
            ),
            models.CheckConstraint(
                check=models.Q(gross_releasable_amount_irr__gt=0),
                name="chk_relinstr_amount_positive",
            ),
        ]

    def __str__(self):
        return f"ReleaseInstruction({self.gross_releasable_amount_irr} IRR, {self.source}) [{self.status}]"


class RefundInstructionSource(models.TextChoices):
    DISPUTE_RESOLUTION = "DISPUTE_RESOLUTION", "Dispute Resolution"
    CANCELLATION = "CANCELLATION", "Cancellation"
    MANUAL = "MANUAL", "Manual"


class RefundInstructionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    INITIATED = "INITIATED", "Initiated"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class RefundInstruction(models.Model):
    """Held-Escrow refund instruction (Section 16) — distinct from a
    post-settlement clawback (out of scope, reserved for PR-E). Represents
    money that was never released past Escrow being returned to the
    customer instead."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="refund_instructions",
    )
    escrow = models.ForeignKey(
        "finance.EscrowRecord",
        on_delete=models.PROTECT,
        related_name="refund_instructions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="refund_instructions",
    )
    invoice = models.ForeignKey(
        "finance.FinancialDocument",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="refund_instructions",
    )
    dispute_resolution = models.ForeignKey(
        "commission.DisputeResolution",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="refund_instructions",
    )

    amount_irr = models.PositiveBigIntegerField()
    reason = models.TextField()
    source = models.CharField(max_length=30, choices=RefundInstructionSource.choices)
    status = models.CharField(
        max_length=20,
        choices=RefundInstructionStatus.choices,
        default=RefundInstructionStatus.PENDING,
        db_index=True,
    )
    psp_reference = models.CharField(max_length=255, blank=True)

    correlation_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_refund_instruction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "escrow", "status"], name="idx_refundinstr_tenant_esc_st"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_refundinstr_tenant_idempotency",
            ),
            models.CheckConstraint(check=models.Q(amount_irr__gt=0), name="chk_refundinstr_amount_positive"),
        ]

    def __str__(self):
        return f"RefundInstruction({self.amount_irr} IRR, {self.source}) [{self.status}]"
