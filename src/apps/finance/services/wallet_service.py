"""
WalletService — Module 05 wallet foundation.

Wallet balances only ever move through append-only WalletTransaction rows.
No code updates WalletAccount.balance except via credit()/debit() here.

LEGACY / FROZEN (as of Module 14): superseded by apps.wallet.services as
the canonical customer-wallet bounded context. Retained only so this
app's own existing tests keep passing — do not extend or wire this into
new flows; use apps.wallet.services.WalletTransactionService instead.
"""

import logging

from django.db import transaction

from apps.kernel.services.event_publisher import EventPublisher

from ..models import DEFAULT_CURRENCY, FinancialDocument, FinancialParty, PaymentTransaction, WalletAccount, WalletTransaction, WalletTransactionType
from .errors import FinanceError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class WalletService:
    """Creates wallets and posts append-only credit/debit movements against them."""

    @classmethod
    def get_or_create_wallet(cls, *, party_id, currency=None) -> WalletAccount:
        party = FinancialParty.objects.get(id=party_id)
        wallet, _ = WalletAccount.objects.get_or_create(
            tenant_id=party.tenant_id,
            party=party,
            currency=currency or DEFAULT_CURRENCY,
        )
        return wallet

    @classmethod
    @transaction.atomic
    def credit(cls, *, wallet_id, amount, source_document_id=None, payment_transaction_id=None, metadata=None) -> WalletTransaction:
        return cls._post(
            wallet_id=wallet_id,
            transaction_type=WalletTransactionType.CREDIT,
            amount=amount,
            source_document_id=source_document_id,
            payment_transaction_id=payment_transaction_id,
            metadata=metadata,
        )

    @classmethod
    @transaction.atomic
    def debit(cls, *, wallet_id, amount, source_document_id=None, payment_transaction_id=None, metadata=None) -> WalletTransaction:
        wallet = WalletAccount.objects.select_for_update().get(id=wallet_id)
        if wallet.balance < amount:
            raise FinanceError(f"Wallet {wallet.id} has insufficient balance for a debit of {amount}.")
        return cls._post(
            wallet=wallet,
            transaction_type=WalletTransactionType.DEBIT,
            amount=-amount,
            source_document_id=source_document_id,
            payment_transaction_id=payment_transaction_id,
            metadata=metadata,
        )

    @classmethod
    @transaction.atomic
    def refund_to_wallet(cls, *, wallet_id, amount, source_document_id=None, payment_transaction_id=None, metadata=None) -> WalletTransaction:
        return cls._post(
            wallet_id=wallet_id,
            transaction_type=WalletTransactionType.REFUND,
            amount=amount,
            source_document_id=source_document_id,
            payment_transaction_id=payment_transaction_id,
            metadata=metadata,
        )

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _post(
        cls, *, transaction_type, amount, wallet=None, wallet_id=None,
        source_document_id=None, payment_transaction_id=None, metadata=None,
    ) -> WalletTransaction:
        if wallet is None:
            wallet = WalletAccount.objects.select_for_update().get(id=wallet_id)

        source_document = None
        if source_document_id:
            source_document = FinancialDocument.objects.get(id=source_document_id)
            if source_document.tenant_id != wallet.tenant_id:
                raise FinanceError("source_document does not belong to the wallet's tenant.")

        payment_transaction = None
        if payment_transaction_id:
            payment_transaction = PaymentTransaction.objects.get(id=payment_transaction_id)
            if payment_transaction.tenant_id != wallet.tenant_id:
                raise FinanceError("payment_transaction does not belong to the wallet's tenant.")

        new_balance = wallet.balance + amount
        wallet_transaction = WalletTransaction.objects.create(
            tenant_id=wallet.tenant_id,
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            source_document=source_document,
            payment_transaction=payment_transaction,
            metadata=metadata or {},
        )

        wallet.balance = new_balance
        wallet.save(update_fields=["balance", "updated_at"])

        EventPublisher.publish(
            tenant_id=wallet.tenant_id,
            event_type="Finance.Wallet.TransactionCreated.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=wallet_transaction.id,
            source_entity_type="WalletTransaction",
            payload={
                "wallet_id": str(wallet.id),
                "transaction_type": transaction_type,
                "amount": str(amount),
                "balance_after": str(new_balance),
            },
        )

        return wallet_transaction
