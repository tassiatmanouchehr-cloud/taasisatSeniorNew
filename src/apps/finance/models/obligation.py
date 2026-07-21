"""FinancialObligation — Module 05 foundation. Who owes whom, and how much."""

import uuid
from decimal import Decimal

from django.db import models

from apps.common.managers import TenantScopedManager

from .document import DEFAULT_CURRENCY, MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class ObligationType(models.TextChoices):
    INVOICE_PAYMENT = "INVOICE_PAYMENT", "Invoice Payment"
    REFUND = "REFUND", "Refund"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    COMMISSION = "COMMISSION", "Commission"


class ObligationStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    DUE = "DUE", "Due"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED", "Partially Resolved"
    RESOLVED = "RESOLVED", "Resolved"
    CANCELLED = "CANCELLED", "Cancelled"
    REVERSED = "REVERSED", "Reversed"
    DISPUTED = "DISPUTED", "Disputed"


OPEN_STATUSES = (ObligationStatus.CREATED, ObligationStatus.DUE, ObligationStatus.PARTIALLY_RESOLVED)


class FinancialObligation(models.Model):
    """A resolvable debt between two FinancialParty records, sourced from a document."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="financial_obligations",
    )
    source_document = models.ForeignKey(
        "finance.FinancialDocument",
        on_delete=models.PROTECT,
        related_name="obligations",
    )
    debtor_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="obligations_owed",
    )
    creditor_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="obligations_receivable",
    )

    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    obligation_type = models.CharField(
        max_length=30,
        choices=ObligationType.choices,
        default=ObligationType.INVOICE_PAYMENT,
    )
    status = models.CharField(
        max_length=20,
        choices=ObligationStatus.choices,
        default=ObligationStatus.CREATED,
        db_index=True,
    )

    due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_financial_obligation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="idx_finoblig_tenant_status"),
        ]

    def __str__(self):
        return (
            f"Obligation {self.id}: {self.debtor_party_id} owes {self.creditor_party_id} {self.amount} [{self.status}]"
        )

    @property
    def resolved_amount(self) -> Decimal:
        return self.amount if self.status == ObligationStatus.RESOLVED else Decimal("0")
