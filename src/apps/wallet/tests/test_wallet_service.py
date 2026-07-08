from decimal import Decimal

from apps.wallet.models import Wallet, WalletBalanceSnapshot
from apps.wallet.services import WalletService, WalletTransactionService

from .helpers import WalletTestCase


class WalletServiceTest(WalletTestCase):
    def test_create_wallet_defaults_to_configured_currency(self):
        self.assertEqual(self.wallet.currency, "IRR")
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    def test_create_wallet_is_idempotent_per_party_and_currency(self):
        second = WalletService.create_wallet(party=self.party)

        self.assertEqual(second.id, self.wallet.id)
        self.assertEqual(Wallet.objects.filter(party=self.party).count(), 1)

    def test_get_balance_returns_cached_balance(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("500"))

        self.wallet.refresh_from_db()
        self.assertEqual(WalletService.get_balance(self.wallet), Decimal("500.00"))

    def test_recalculate_balance_matches_transaction_sum(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("1000"))
        WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("300"))
        WalletTransactionService.refund(wallet_id=self.wallet.id, amount=Decimal("50"))

        recalculated = WalletService.recalculate_balance(self.wallet)

        self.assertEqual(recalculated, Decimal("750.00"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("750.00"))

        snapshot = WalletBalanceSnapshot.objects.get(wallet=self.wallet)
        self.assertEqual(snapshot.balance, Decimal("750.00"))
        self.assertEqual(snapshot.transaction_count, 3)

    def test_recalculate_balance_repairs_drift(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("200"))

        # Simulate cache drift directly on the denormalized field.
        Wallet.objects.filter(id=self.wallet.id).update(balance=Decimal("999999.99"))

        recalculated = WalletService.recalculate_balance(self.wallet)

        self.assertEqual(recalculated, Decimal("200.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("200.00"))

    def test_recalculate_balance_with_no_transactions(self):
        recalculated = WalletService.recalculate_balance(self.wallet)

        self.assertEqual(recalculated, Decimal("0.00"))
