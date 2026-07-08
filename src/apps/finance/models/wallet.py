"""
WalletAccount / WalletTransaction — Module 05 wallet foundation. Entries are append-only.

LEGACY / FROZEN (as of Module 14): superseded by apps.wallet as the
canonical customer-wallet bounded context. Nothing outside this app's own
tests ever creates a WalletAccount row. Kept only so those existing tests
keep passing — do not extend this model or wire it into new flows; build
new wallet/customer-credit functionality in apps.wallet instead.
"""

import uuid
from decimal import Decimal

from django.db import models

from apps.common.managers import TenantScopedManager

from .document import DEFAULT_CURRENCY, MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class WalletStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    CLOSED = "CLOSED", "Closed"


class WalletTransactionType(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    DEBIT = "DEBIT", "Debit"
    HOLD = "HOLD", "Hold"
    RELEASE = "RELEASE", "Release"
    REFUND = "REFUND", "Refund"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class WalletAccount(models.Model):
    """One balance-holding account per (tenant, party, currency)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="wallet_accounts",
    )
    party = models.ForeignKey(
        "finance.FinancialParty", on_delete=models.PROTECT, related_name="wallets",
    )

    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    balance = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=WalletStatus.choices, default=WalletStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_wallet_account"
        ordering = ["-created_at"]
        unique_together = [("tenant", "party", "currency")]

    def __str__(self):
        return f"Wallet({self.party_id}, {self.currency}) = {self.balance}"


class WalletTransaction(models.Model):
    """Append-only ledger of movements against a WalletAccount."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="wallet_transactions",
    )
    wallet = models.ForeignKey(
        "finance.WalletAccount", on_delete=models.PROTECT, related_name="transactions",
    )

    transaction_type = models.CharField(max_length=20, choices=WalletTransactionType.choices)
    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    balance_after = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)

    source_document = models.ForeignKey(
        "finance.FinancialDocument", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="wallet_transactions",
    )
    payment_transaction = models.ForeignKey(
        "finance.PaymentTransaction", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="wallet_transactions",
    )
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_wallet_transaction"
        ordering = ["-created_at"]

    def __str__(self):
        return f"WalletTransaction {self.transaction_type} {self.amount} -> {self.balance_after}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("WalletTransaction is append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("WalletTransaction is append-only and cannot be deleted.")
