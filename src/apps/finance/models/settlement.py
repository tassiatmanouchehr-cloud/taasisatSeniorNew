"""SettlementBatch / SettlementItem — Module 05 settlement/netting foundation. No real payout."""

import uuid
from decimal import Decimal

from django.db import models

from apps.common.managers import TenantScopedManager

from .document import DEFAULT_CURRENCY, MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class SettlementBatchStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    CALCULATED = "CALCULATED", "Calculated"
    APPROVED = "APPROVED", "Approved"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"


class SettlementItemStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"


class SettlementBatch(models.Model):
    """A calculated net-position run across FinancialParty records for a period."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="settlement_batches",
    )

    status = models.CharField(
        max_length=20,
        choices=SettlementBatchStatus.choices,
        default=SettlementBatchStatus.DRAFT,
        db_index=True,
    )
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0")
    )
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_settlement_batch"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SettlementBatch {self.id} [{self.status}] {self.total_amount} {self.currency}"


class SettlementItem(models.Model):
    """Net position for one FinancialParty within a SettlementBatch."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="settlement_items",
    )
    batch = models.ForeignKey(
        "finance.SettlementBatch",
        on_delete=models.CASCADE,
        related_name="items",
    )
    party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="settlement_items",
    )

    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    status = models.CharField(
        max_length=20,
        choices=SettlementItemStatus.choices,
        default=SettlementItemStatus.PENDING,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "finance_settlement_item"
        ordering = ["party_id"]
        unique_together = [("batch", "party")]

    def __str__(self):
        return f"SettlementItem(batch={self.batch_id}, party={self.party_id}) = {self.amount}"
