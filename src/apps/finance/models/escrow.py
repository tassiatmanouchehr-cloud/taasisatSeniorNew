"""
EscrowRecord — Module 05 escrow foundation, extended for Financial Core
PR-B (Real Escrow, Objection Period, Disputes & Partial Release).

The original HELD/RELEASED/REFUNDED/CANCELLED shape (and the `amount`/
`beneficiary_party`/`release()`/`refund()` single-beneficiary methods on
EscrowService) was a pre-Financial-Core scaffold with zero real callers —
confirmed by inspection before PR-B: nothing outside its own module and
tests ever referenced EscrowRecord/EscrowService. It is kept, unused but
harmless, for backward compatibility; PR-B's real production path uses the
fields/statuses added below instead.

PR-B's Escrow deliberately has no single `beneficiary_party` — money held
here is not yet allocated to any one party. Multi-party allocation
(platform/company/caregiver shares, computed from the frozen
apps.commission.CommissionSnapshot via apps.commission's
AllocationCalculator) and the actual wallet credit belong to PR-C, which
consumes a `ReleaseInstruction` (apps.commission.models.release_instruction)
to do so. PR-B only ever produces those immutable instructions — it never
credits a wallet itself.

Every PR-B monetary field is an integer count of whole Rials (no
fractional subunit — matches apps.commission.services.allocation_calculator
.AllocationCalculator's own "deterministic integer-IRR" convention), unlike
the surrounding Decimal-based finance/payments/pricing models (which this
migration does not touch or redesign).

Mandatory invariant, enforced at the database level (see Meta.constraints):

    original_amount_irr
    = released_amount_irr + refunded_amount_irr + blocked_amount_irr + remaining_amount_irr

`held_amount_irr` and `releasable_amount_irr` are not part of that
equation — they are derived/auxiliary: held_amount_irr is always
blocked_amount_irr + remaining_amount_irr (the total still parked in
escrow, whether disputed or not); releasable_amount_irr is always a
subset of remaining_amount_irr (the portion that has cleared objection/
dispute review and is ready for a ReleaseInstruction to consume it) — both
are kept in sync by apps.finance.services.escrow_service.EscrowService's
new methods, and both are also database-constrained.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager

from .document import DEFAULT_CURRENCY, MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class EscrowStatus(models.TextChoices):
    HELD = "HELD", "Held"
    RELEASED = "RELEASED", "Released"
    REFUNDED = "REFUNDED", "Refunded"
    CANCELLED = "CANCELLED", "Cancelled"
    # Added for Financial Core PR-B — see module docstring.
    PARTIALLY_RELEASED = "PARTIALLY_RELEASED", "Partially Released"
    FULLY_RELEASED = "FULLY_RELEASED", "Fully Released"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially Refunded"
    FULLY_REFUNDED = "FULLY_REFUNDED", "Fully Refunded"
    CLOSED = "CLOSED", "Closed"


# PR-B statuses considered "still open" (blocked/remaining money may still
# move) — a record in any other status has nothing left to release/refund.
OPEN_ESCROW_STATUSES = (
    EscrowStatus.HELD,
    EscrowStatus.PARTIALLY_RELEASED,
    EscrowStatus.PARTIALLY_REFUNDED,
)


class EscrowMovementType(models.TextChoices):
    HOLD = "HOLD", "Hold"
    MARK_RELEASABLE = "MARK_RELEASABLE", "Mark Releasable"
    BLOCK_FOR_DISPUTE = "BLOCK_FOR_DISPUTE", "Block For Dispute"
    UNBLOCK = "UNBLOCK", "Unblock"
    RELEASE = "RELEASE", "Release"
    REFUND = "REFUND", "Refund"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class EscrowRecord(models.Model):
    """Funds held against a document pending release or refund."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="escrow_records",
    )
    source_document = models.ForeignKey(
        "finance.FinancialDocument",
        on_delete=models.PROTECT,
        related_name="escrow_records",
    )
    payer_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="escrow_as_payer",
    )
    beneficiary_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escrow_as_beneficiary",
    )

    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    status = models.CharField(max_length=20, choices=EscrowStatus.choices, default=EscrowStatus.HELD, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    # --- Financial Core PR-B additions -------------------------------------

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="escrow_records",
    )
    payment_transaction = models.ForeignKey(
        "finance.PaymentTransaction",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="escrow_records",
    )
    commission_snapshot = models.ForeignKey(
        "commission.CommissionSnapshot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="escrow_records",
    )
    correlation_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)

    original_amount_irr = models.PositiveBigIntegerField(default=0)
    held_amount_irr = models.PositiveBigIntegerField(default=0)
    releasable_amount_irr = models.PositiveBigIntegerField(default=0)
    blocked_amount_irr = models.PositiveBigIntegerField(default=0)
    released_amount_irr = models.PositiveBigIntegerField(default=0)
    refunded_amount_irr = models.PositiveBigIntegerField(default=0)
    remaining_amount_irr = models.PositiveBigIntegerField(default=0)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_escrow_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="idx_finescrow_tenant_status"),
            models.Index(fields=["tenant", "order", "status"], name="idx_finescrow_tenant_order_st"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_escrow_tenant_idempotency",
            ),
            models.CheckConstraint(
                check=models.Q(
                    original_amount_irr=(
                        models.F("released_amount_irr")
                        + models.F("refunded_amount_irr")
                        + models.F("blocked_amount_irr")
                        + models.F("remaining_amount_irr")
                    ),
                ),
                name="chk_escrow_conservation",
            ),
            models.CheckConstraint(
                check=models.Q(held_amount_irr=models.F("blocked_amount_irr") + models.F("remaining_amount_irr")),
                name="chk_escrow_held_derived",
            ),
            models.CheckConstraint(
                check=models.Q(releasable_amount_irr__lte=models.F("remaining_amount_irr")),
                name="chk_escrow_releasable_within_remaining",
            ),
        ]

    def __str__(self):
        return f"Escrow {self.id}: {self.amount} {self.currency} [{self.status}]"


class EscrowMovement(models.Model):
    """Append-only record of one money-state change against an EscrowRecord.

    Immutable by construction (save()/delete() below), mirroring
    apps.payments.models.PaymentCallback and
    apps.commission.models.deadline.PaymentDeadlineExtension — the
    established append-only pattern in this codebase. Every real balance
    change to an EscrowRecord happens through exactly one EscrowMovement,
    created inside the same transaction as the EscrowRecord field update
    (see apps.finance.services.escrow_service.EscrowService)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="escrow_movements",
    )
    escrow = models.ForeignKey(
        "finance.EscrowRecord",
        on_delete=models.PROTECT,
        related_name="movements",
    )

    movement_type = models.CharField(max_length=20, choices=EscrowMovementType.choices, db_index=True)
    amount_irr = models.PositiveBigIntegerField()

    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)

    source_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="What caused this movement, e.g. 'ObjectionPeriod', 'Dispute', 'DisputeResolution'.",
    )
    source_id = models.UUIDField(null=True, blank=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    correlation_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_escrow_movement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "escrow", "movement_type"], name="idx_escrowmove_tenant_esc_type"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_escrowmovement_tenant_idempotency",
            ),
        ]

    def __str__(self):
        return f"EscrowMovement({self.movement_type}, {self.amount_irr}) on {self.escrow_id}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("EscrowMovement is append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("EscrowMovement is append-only and cannot be deleted.")
