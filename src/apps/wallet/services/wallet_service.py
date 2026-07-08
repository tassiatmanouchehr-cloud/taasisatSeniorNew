"""
WalletService — Module 14 foundation.

Creates wallets and recalculates their deterministic balance. Wallet
ownership is expressed via apps.finance.models.FinancialParty — the only
"existing financial abstraction" this app depends on.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum

from .configuration import WalletConfiguration
from .errors import WalletError

QUANT = Decimal("0.01")


def _q(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)


class WalletService:
    """Creates Wallet rows and recomputes their deterministic balance."""

    @classmethod
    @transaction.atomic
    def create_wallet(cls, *, party, currency=None):
        from ..models import Wallet

        if not party.tenant_id:
            raise WalletError("Cannot create a Wallet without a tenant_id on the party.")

        currency = currency or WalletConfiguration.get_default_currency(tenant_id=party.tenant_id)

        wallet, _ = Wallet.objects.get_or_create(
            tenant_id=party.tenant_id,
            party=party,
            currency=currency,
        )
        return wallet

    @classmethod
    def get_or_create_wallet(cls, *, party, currency=None):
        return cls.create_wallet(party=party, currency=currency)

    @classmethod
    def get_balance(cls, wallet) -> Decimal:
        return wallet.balance

    @classmethod
    @transaction.atomic
    def recalculate_balance(cls, wallet):
        """Recomputes the deterministic sum of transactions and realigns the cached balance + snapshot."""
        from ..models import Wallet, WalletBalanceSnapshot, WalletTransaction

        wallet = Wallet.objects.select_for_update().get(id=wallet.id)

        aggregate = WalletTransaction.objects.filter(wallet=wallet).aggregate(
            total=Sum("amount"),
        )
        true_balance = _q(aggregate["total"] or Decimal("0"))
        transaction_count = WalletTransaction.objects.filter(wallet=wallet).count()

        if wallet.balance != true_balance:
            wallet.balance = true_balance
            wallet.save(update_fields=["balance", "updated_at"])

        WalletBalanceSnapshot.objects.update_or_create(
            wallet=wallet,
            defaults={
                "tenant_id": wallet.tenant_id,
                "balance": true_balance,
                "transaction_count": transaction_count,
            },
        )

        return true_balance
