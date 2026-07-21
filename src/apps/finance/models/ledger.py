"""
LedgerEntry — Module 05 immutable ledger foundation.

Append-only. Entries are only ever created via
apps.finance.services.ledger_service.LedgerService, which enforces that
debit total == credit total for every entry_group_id. No code — including
this model — may update or delete a LedgerEntry once created, and nothing
may post directly from ExecutionSession; every entry must reference a
document, payment, or obligation.
"""

import uuid

from django.db import models
from django.db.models import Q

from apps.common.managers import TenantScopedManager

from .document import DEFAULT_CURRENCY, MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class LedgerEntryType(models.TextChoices):
    DEBIT = "DEBIT", "Debit"
    CREDIT = "CREDIT", "Credit"


class LedgerEntry(models.Model):
    """One immutable, balanced-in-aggregate debit or credit line."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    entry_group_id = models.UUIDField(
        db_index=True,
        help_text="Groups the balanced set of debit/credit entries posted together.",
    )
    party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )

    source_document = models.ForeignKey(
        "finance.FinancialDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    payment_transaction = models.ForeignKey(
        "finance.PaymentTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    obligation = models.ForeignKey(
        "finance.FinancialObligation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )

    entry_type = models.CharField(max_length=10, choices=LedgerEntryType.choices)
    account_code = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    description = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_ledger_entry"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["tenant", "entry_group_id"], name="idx_finledger_tenant_group"),
            models.Index(fields=["tenant", "party", "account_code"], name="idx_finledger_party_acct"),
        ]
        constraints = [
            # Database-level backstop (Epic 03 Sprint 1 remediation): the same
            # payment_transaction can never post the same account_code twice.
            # Scoped to payment_transaction IS NOT NULL — postings referencing
            # only a source_document/obligation are unaffected.
            models.UniqueConstraint(
                fields=["payment_transaction", "account_code"],
                condition=Q(payment_transaction__isnull=False),
                name="uq_ledger_entry_payment_txn_account_code",
            ),
        ]

    def __str__(self):
        return f"LedgerEntry {self.entry_type} {self.amount} {self.currency} ({self.account_code})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("LedgerEntry is immutable and cannot be modified after creation.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("LedgerEntry is immutable and cannot be deleted.")
