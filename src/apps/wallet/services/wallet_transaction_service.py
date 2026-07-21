"""
WalletTransactionService — Module 14 foundation.

The only code that creates WalletTransaction rows. Every balance change is
represented by exactly one append-only transaction; Wallet.balance is a
denormalized cache kept in lock-step with it (see WalletService.
recalculate_balance for drift repair). All mutations are Decimal-only,
tenant-aware, and idempotent when an idempotency_key is supplied.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction

from ..models import Wallet, WalletTransaction, WalletTransactionType
from .configuration import WalletConfiguration
from .errors import WalletError

QUANT = Decimal("0.01")


def _q(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)


class WalletTransactionService:
    """Posts CREDIT/DEBIT/REFUND/PROMOTION/ADJUSTMENT/MANUAL movements against a Wallet."""

    @classmethod
    def list_transactions(cls, wallet):
        """Read-only. Returns the wallet's transactions ordered newest-first as a QuerySet
        (callers may further filter/slice/paginate it — no rows are fetched until they do)."""
        return WalletTransaction.objects.filter(tenant_id=wallet.tenant_id, wallet=wallet).order_by("-created_at")

    @classmethod
    def validate_sufficient_funds(cls, wallet, amount) -> bool:
        """True if applying `amount` (signed) would not take the wallet negative, or overdraft is allowed."""
        amount = _q(amount)
        if wallet.balance + amount >= Decimal("0"):
            return True
        return WalletConfiguration.get_overdraft_enabled(tenant_id=wallet.tenant_id)

    @classmethod
    @transaction.atomic
    def credit(cls, *, wallet_id, amount, reason="", metadata=None, idempotency_key=None) -> WalletTransaction:
        amount = _q(amount)
        if amount <= 0:
            raise WalletError("Credit amount must be positive.")
        return cls._apply(
            wallet_id=wallet_id,
            transaction_type=WalletTransactionType.CREDIT,
            amount=amount,
            reason=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    @classmethod
    @transaction.atomic
    def debit(cls, *, wallet_id, amount, reason="", metadata=None, idempotency_key=None) -> WalletTransaction:
        amount = _q(amount)
        if amount <= 0:
            raise WalletError("Debit amount must be positive.")
        return cls._apply(
            wallet_id=wallet_id,
            transaction_type=WalletTransactionType.DEBIT,
            amount=-amount,
            reason=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    @classmethod
    @transaction.atomic
    def refund(cls, *, wallet_id, amount, reason="", metadata=None, idempotency_key=None) -> WalletTransaction:
        amount = _q(amount)
        if amount <= 0:
            raise WalletError("Refund amount must be positive.")
        return cls._apply(
            wallet_id=wallet_id,
            transaction_type=WalletTransactionType.REFUND,
            amount=amount,
            reason=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    @classmethod
    @transaction.atomic
    def promotion_credit(
        cls, *, wallet_id, amount, reason="", metadata=None, idempotency_key=None
    ) -> WalletTransaction:
        amount = _q(amount)
        if amount <= 0:
            raise WalletError("Promotion credit amount must be positive.")
        return cls._apply(
            wallet_id=wallet_id,
            transaction_type=WalletTransactionType.PROMOTION,
            amount=amount,
            reason=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    @classmethod
    @transaction.atomic
    def adjust(cls, *, wallet_id, amount, reason="", metadata=None, idempotency_key=None) -> WalletTransaction:
        """System/operator correction. Signed. Bounded by wallet.max_manual_adjustment."""
        amount = _q(amount)
        wallet = Wallet.objects.select_for_update().get(id=wallet_id)
        cls._enforce_adjustment_cap(wallet, amount)
        return cls._apply(
            wallet=wallet,
            transaction_type=WalletTransactionType.ADJUSTMENT,
            amount=amount,
            reason=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    @classmethod
    @transaction.atomic
    def manual_adjustment(
        cls, *, wallet_id, amount, reason="", metadata=None, idempotency_key=None
    ) -> WalletTransaction:
        """Operator-initiated manual credit/debit. Signed. Bounded by wallet.max_manual_adjustment."""
        amount = _q(amount)
        wallet = Wallet.objects.select_for_update().get(id=wallet_id)
        cls._enforce_adjustment_cap(wallet, amount)
        return cls._apply(
            wallet=wallet,
            transaction_type=WalletTransactionType.MANUAL,
            amount=amount,
            reason=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _enforce_adjustment_cap(cls, wallet, amount):
        max_adjustment = WalletConfiguration.get_max_manual_adjustment(tenant_id=wallet.tenant_id)
        if max_adjustment is not None and abs(amount) > max_adjustment:
            raise WalletError(
                f"Adjustment amount {amount} exceeds the configured maximum of {max_adjustment}.",
            )

    @classmethod
    def _apply(
        cls,
        *,
        transaction_type,
        amount,
        wallet=None,
        wallet_id=None,
        reason="",
        metadata=None,
        idempotency_key=None,
    ) -> WalletTransaction:
        if wallet is None:
            wallet = Wallet.objects.select_for_update().get(id=wallet_id)

        if idempotency_key:
            existing = WalletTransaction.objects.filter(
                wallet=wallet,
                idempotency_key=idempotency_key,
            ).first()
            if existing is not None:
                return existing

        if amount < 0 and not cls.validate_sufficient_funds(wallet, amount):
            raise WalletError(
                f"Wallet {wallet.id} has insufficient balance for a movement of {amount} "
                f"(balance={wallet.balance}, overdraft disabled).",
            )

        new_balance = _q(wallet.balance + amount)

        try:
            with transaction.atomic():
                wallet_transaction = WalletTransaction.objects.create(
                    tenant_id=wallet.tenant_id,
                    wallet=wallet,
                    transaction_type=transaction_type,
                    amount=amount,
                    balance_after=new_balance,
                    idempotency_key=idempotency_key,
                    reason=reason,
                    metadata=metadata or {},
                )
        except IntegrityError:
            existing = WalletTransaction.objects.filter(
                wallet=wallet,
                idempotency_key=idempotency_key,
            ).first()
            if existing is not None and idempotency_key:
                return existing
            raise

        wallet.balance = new_balance
        wallet.save(update_fields=["balance", "updated_at"])

        return wallet_transaction
