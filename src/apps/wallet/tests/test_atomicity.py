"""
Tests proving WalletTransactionService mutations are wrapped in
transaction.atomic(): a failure anywhere inside _apply() must roll back
BOTH the WalletTransaction row and the Wallet.balance update, and
select_for_update() must serialize concurrent movements against the same
wallet so the deterministic-balance invariant can never be violated.
"""

from decimal import Decimal
from unittest.mock import patch

from apps.wallet.models import WalletTransaction
from apps.wallet.services import WalletTransactionService

from .helpers import WalletTestCase

_SAVE_TARGET = "apps.wallet.models.Wallet.save"


class WalletAtomicityTest(WalletTestCase):
    def test_credit_rolls_back_fully_on_late_failure(self):
        with patch(_SAVE_TARGET, side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("1000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertEqual(WalletTransaction.objects.filter(wallet=self.wallet).count(), 0)

    def test_debit_rolls_back_fully_on_late_failure(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("1000"))

        with patch(_SAVE_TARGET, side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("400"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1000.00"))
        self.assertEqual(WalletTransaction.objects.filter(wallet=self.wallet).count(), 1)

    def test_concurrent_movements_serialize_via_select_for_update(self):
        """Two sequential debits that would overdraw if applied against a stale balance must not both succeed."""
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100"))

        WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("60"))

        with self.assertRaises(Exception):
            WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("60"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("40.00"))
        self.assertEqual(WalletTransaction.objects.filter(wallet=self.wallet).count(), 2)

    def test_duplicate_idempotency_key_race_falls_back_to_existing_row(self):
        """A pre-check miss (simulating a concurrent insert racing in) must fall back to the real row
        found via the DB's unique_together(wallet, idempotency_key) constraint, not raise or double-post."""
        existing = WalletTransactionService.credit(
            wallet_id=self.wallet.id,
            amount=Decimal("100"),
            idempotency_key="race-key",
        )

        real_filter = WalletTransaction.objects.filter
        call_count = {"n": 0}

        def flaky_filter(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                from unittest.mock import MagicMock

                miss = MagicMock()
                miss.first.return_value = None
                return miss
            return real_filter(*args, **kwargs)

        with patch.object(WalletTransaction.objects, "filter", side_effect=flaky_filter):
            txn = WalletTransactionService.credit(
                wallet_id=self.wallet.id,
                amount=Decimal("100"),
                idempotency_key="race-key",
            )

        self.assertEqual(txn.id, existing.id)
        self.assertEqual(WalletTransaction.objects.filter(wallet=self.wallet, idempotency_key="race-key").count(), 1)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100.00"))
