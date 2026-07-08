from decimal import Decimal

from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.wallet.models import WalletTransaction, WalletTransactionType
from apps.wallet.services import WalletError, WalletTransactionService

from .helpers import WalletTestCase


def _set_tenant_config(tenant_id, key, value, value_type=ValueType.BOOLEAN):
    config_key, _ = ConfigurationKey.objects.get_or_create(
        key=key,
        defaults={"owner_module": "M14", "value_type": value_type, "scope_level": ScopeLevel.TENANT},
    )
    ConfigurationValue.objects.update_or_create(
        tenant_id=tenant_id, config_key=config_key, scope_type=ScopeLevel.TENANT,
        defaults={"value": value, "is_active": True},
    )


class WalletTransactionServiceTest(WalletTestCase):
    def test_credit_increases_balance(self):
        txn = WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100000.00"))
        self.assertEqual(txn.transaction_type, WalletTransactionType.CREDIT)
        self.assertEqual(txn.amount, Decimal("100000.00"))
        self.assertEqual(txn.balance_after, Decimal("100000.00"))

    def test_debit_decreases_balance(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100000"))
        txn = WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("40000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("60000.00"))
        self.assertEqual(txn.transaction_type, WalletTransactionType.DEBIT)
        self.assertEqual(txn.amount, Decimal("-40000.00"))

    def test_refund_increases_balance(self):
        txn = WalletTransactionService.refund(wallet_id=self.wallet.id, amount=Decimal("25000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("25000.00"))
        self.assertEqual(txn.transaction_type, WalletTransactionType.REFUND)

    def test_promotion_credit_increases_balance(self):
        txn = WalletTransactionService.promotion_credit(wallet_id=self.wallet.id, amount=Decimal("15000"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("15000.00"))
        self.assertEqual(txn.transaction_type, WalletTransactionType.PROMOTION)

    def test_manual_adjustment_can_be_negative_or_positive(self):
        WalletTransactionService.manual_adjustment(wallet_id=self.wallet.id, amount=Decimal("1000"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1000.00"))

        WalletTransactionService.manual_adjustment(wallet_id=self.wallet.id, amount=Decimal("-400"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("600.00"))

    def test_manual_adjustment_respects_max_cap(self):
        _set_tenant_config(self.tenant.id, "wallet.max_manual_adjustment", 500, value_type=ValueType.NUMBER)

        with self.assertRaises(WalletError):
            WalletTransactionService.manual_adjustment(wallet_id=self.wallet.id, amount=Decimal("501"))

        # Within the cap succeeds.
        WalletTransactionService.manual_adjustment(wallet_id=self.wallet.id, amount=Decimal("500"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("500.00"))

    def test_adjust_creates_adjustment_transaction(self):
        txn = WalletTransactionService.adjust(wallet_id=self.wallet.id, amount=Decimal("300"))

        self.assertEqual(txn.transaction_type, WalletTransactionType.ADJUSTMENT)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("300.00"))

    def test_debit_rejects_insufficient_funds_by_default(self):
        with self.assertRaises(WalletError):
            WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("1"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    def test_debit_allowed_when_overdraft_enabled(self):
        _set_tenant_config(self.tenant.id, "wallet.overdraft.enabled", True)

        txn = WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("50"))

        self.assertEqual(txn.amount, Decimal("-50.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("-50.00"))

    def test_validate_sufficient_funds(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100"))
        self.wallet.refresh_from_db()

        self.assertTrue(WalletTransactionService.validate_sufficient_funds(self.wallet, Decimal("-100")))
        self.assertFalse(WalletTransactionService.validate_sufficient_funds(self.wallet, Decimal("-101")))

    def test_credit_and_debit_amounts_must_be_positive(self):
        with self.assertRaises(WalletError):
            WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("0"))

        with self.assertRaises(WalletError):
            WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("-5"))

    def test_transaction_is_append_only(self):
        txn = WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("1000"))

        with self.assertRaises(ValueError):
            txn.amount = Decimal("999")
            txn.save()

        with self.assertRaises(ValueError):
            txn.delete()

    def test_deterministic_balance_equals_transaction_sum(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("1000"))
        WalletTransactionService.debit(wallet_id=self.wallet.id, amount=Decimal("250"))
        WalletTransactionService.refund(wallet_id=self.wallet.id, amount=Decimal("10"))
        WalletTransactionService.promotion_credit(wallet_id=self.wallet.id, amount=Decimal("5"))

        total = sum(
            (t.amount for t in WalletTransaction.objects.filter(wallet=self.wallet)), Decimal("0"),
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, total)
        self.assertEqual(self.wallet.balance, Decimal("765.00"))

    def test_decimal_precision_is_preserved(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100.005"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100.01"))

    def test_idempotency_key_prevents_duplicate_transaction(self):
        first = WalletTransactionService.credit(
            wallet_id=self.wallet.id, amount=Decimal("100"), idempotency_key="op-123",
        )
        second = WalletTransactionService.credit(
            wallet_id=self.wallet.id, amount=Decimal("100"), idempotency_key="op-123",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(WalletTransaction.objects.filter(wallet=self.wallet).count(), 1)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100.00"))

    def test_idempotency_key_is_scoped_per_wallet(self):
        other_customer = self._create_customer(tenant=self.tenant, display_name="Second Customer")
        from apps.finance.services import FinancialPartyService
        from apps.wallet.services import WalletService

        other_party = FinancialPartyService.resolve_party_for_customer(other_customer)
        other_wallet = WalletService.create_wallet(party=other_party)

        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100"), idempotency_key="shared-key")
        WalletTransactionService.credit(wallet_id=other_wallet.id, amount=Decimal("100"), idempotency_key="shared-key")

        self.assertEqual(WalletTransaction.objects.filter(idempotency_key="shared-key").count(), 2)

    def test_different_idempotency_keys_both_apply(self):
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100"), idempotency_key="a")
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("100"), idempotency_key="b")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("200.00"))
