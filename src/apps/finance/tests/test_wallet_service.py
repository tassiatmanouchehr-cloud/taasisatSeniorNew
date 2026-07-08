"""Tests for WalletService credit/debit and append-only wallet transactions."""

from decimal import Decimal

from apps.finance.models import WalletTransaction, WalletTransactionType
from apps.finance.services import FinanceError, FinancialPartyService, WalletService

from .helpers import FinanceTestCase


class WalletServiceTest(FinanceTestCase):
    def setUp(self):
        super().setUp()
        self.party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        self.wallet = WalletService.get_or_create_wallet(party_id=self.party.id)

    def test_credit_increases_balance(self):
        WalletService.credit(wallet_id=self.wallet.id, amount=Decimal("100000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100000"))

    def test_debit_decreases_balance(self):
        WalletService.credit(wallet_id=self.wallet.id, amount=Decimal("100000"))
        WalletService.debit(wallet_id=self.wallet.id, amount=Decimal("40000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("60000"))

    def test_debit_rejects_insufficient_balance(self):
        with self.assertRaises(FinanceError):
            WalletService.debit(wallet_id=self.wallet.id, amount=Decimal("1"))

    def test_refund_to_wallet(self):
        WalletService.refund_to_wallet(wallet_id=self.wallet.id, amount=Decimal("25000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("25000"))
        txn = WalletTransaction.objects.get(wallet=self.wallet)
        self.assertEqual(txn.transaction_type, WalletTransactionType.REFUND)

    def test_wallet_transaction_is_append_only(self):
        txn = WalletService.credit(wallet_id=self.wallet.id, amount=Decimal("1000"))

        with self.assertRaises(ValueError):
            txn.amount = Decimal("999")
            txn.save()

        with self.assertRaises(ValueError):
            txn.delete()
