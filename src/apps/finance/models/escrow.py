"""EscrowRecord — Module 05 escrow foundation. No real bank transfer."""

import uuid

from django.db import models

from apps.common.managers import TenantScopedManager

from .document import DEFAULT_CURRENCY, MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class EscrowStatus(models.TextChoices):
    HELD = "HELD", "Held"
    RELEASED = "RELEASED", "Released"
    REFUNDED = "REFUNDED", "Refunded"
    CANCELLED = "CANCELLED", "Cancelled"


class EscrowRecord(models.Model):
    """Funds held against a document pending release or refund."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="escrow_records",
    )
    source_document = models.ForeignKey(
        "finance.FinancialDocument", on_delete=models.PROTECT, related_name="escrow_records",
    )
    payer_party = models.ForeignKey(
        "finance.FinancialParty", on_delete=models.PROTECT, related_name="escrow_as_payer",
    )
    beneficiary_party = models.ForeignKey(
        "finance.FinancialParty", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="escrow_as_beneficiary",
    )

    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    status = models.CharField(max_length=20, choices=EscrowStatus.choices, default=EscrowStatus.HELD, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_escrow_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="idx_finescrow_tenant_status"),
        ]

    def __str__(self):
        return f"Escrow {self.id}: {self.amount} {self.currency} [{self.status}]"
