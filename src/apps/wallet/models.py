"""
Wallet & Customer Credits — Module 14 foundation.

Internal stored value only — not a payment gateway. Wallet ownership is
expressed via apps.finance.models.FinancialParty (the existing generic
financial-counterparty abstraction resolved by
apps.finance.services.party_service.FinancialPartyService), never by a
duplicate FK straight to CustomerProfile/ServiceSupplier.

This app is a standalone bounded context: it does not import from, or get
imported by, apps.finance/booking/pricing/orders at runtime. Future payment
provider modules call WalletTransactionService directly.

Money constants are intentionally duplicated (not imported) from
apps.finance.models.document to avoid a runtime dependency on apps.finance.
"""

import uuid
from decimal import Decimal

from django.db import models

from apps.common.managers import TenantScopedManager

MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2
DEFAULT_CURRENCY = "IRR"


class WalletStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    CLOSED = "CLOSED", "Closed"


class WalletTransactionType(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    DEBIT = "DEBIT", "Debit"
    REFUND = "REFUND", "Refund"
    PROMOTION = "PROMOTION", "Promotion"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    MANUAL = "MANUAL", "Manual"


class Wallet(models.Model):
    """One balance-holding wallet per (tenant, party, currency)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="wallets",
    )
    party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="internal_wallets",
    )

    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    balance = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    status = models.CharField(max_length=20, choices=WalletStatus.choices, default=WalletStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "wallet_wallet"
        ordering = ["-created_at"]
        unique_together = [("tenant", "party", "currency")]

    def __str__(self):
        return f"Wallet({self.party_id}, {self.currency}) = {self.balance}"


class WalletTransaction(models.Model):
    """Append-only ledger of movements against a Wallet."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="internal_wallet_transactions",
    )
    wallet = models.ForeignKey(
        "wallet.Wallet",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    transaction_type = models.CharField(max_length=20, choices=WalletTransactionType.choices)
    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    balance_after = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)

    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "wallet_wallet_transaction"
        ordering = ["-created_at"]
        unique_together = [("wallet", "idempotency_key")]

    def __str__(self):
        return f"WalletTransaction {self.transaction_type} {self.amount} -> {self.balance_after}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("WalletTransaction is append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("WalletTransaction is append-only and cannot be deleted.")


class WalletBalanceSnapshot(models.Model):
    """Auditable checkpoint of a deterministic balance recalculation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="wallet_balance_snapshots",
    )
    wallet = models.OneToOneField(
        "wallet.Wallet",
        on_delete=models.CASCADE,
        related_name="balance_snapshot",
    )
    balance = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    transaction_count = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "wallet_balance_snapshot"

    def __str__(self):
        return f"WalletBalanceSnapshot(wallet={self.wallet_id}, balance={self.balance}, n={self.transaction_count})"
