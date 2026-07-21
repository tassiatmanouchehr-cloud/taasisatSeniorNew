"""
Proves apps.payments' settlement wiring stays narrowly scoped.

Sprint 1 (Epic 03) wires PaymentCallbackService to
SettlementOrchestrationService, which *does* now create a
finance.PaymentTransaction and credit an apps.wallet.Wallet — but only for
a PaymentIntent that references an Order (reference_type="Order"). The
default PaymentsTestCase fixture's `self.intent` has no reference_type set,
which is exactly the documented Sprint 1 limitation (see
SettlementOrchestrationService's docstring): settlement is skipped, not
silently faked, for non-Order-referencing intents. These tests guard that
skip path. The full settle-and-credit happy path is covered separately in
test_settlement_orchestration.py.

The legacy, frozen apps.finance.models.wallet.WalletAccount/WalletTransaction
must never be touched by any payments flow, Order-referencing or not — that
guardrail is unconditional and covered here.
"""

from apps.finance.models import PaymentTransaction
from apps.finance.services import WalletService as LegacyFinanceWalletService
from apps.payments.services import PaymentCallbackService, PaymentIntentService
from apps.wallet.models import Wallet, WalletTransaction

from .helpers import PaymentsTestCase


class PaymentNoSideEffectsTest(PaymentsTestCase):
    def test_callback_for_non_order_intent_does_not_touch_wallet_app(self):
        assert self.intent.reference_type != "Order"
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        payload = self._success_payload(attempt)

        wallet_count_before = Wallet.objects.count()
        wallet_txn_count_before = WalletTransaction.objects.count()

        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference,
            payload=payload,
        )

        self.assertEqual(Wallet.objects.count(), wallet_count_before)
        self.assertEqual(WalletTransaction.objects.count(), wallet_txn_count_before)

    def test_successful_callback_does_not_touch_legacy_finance_wallet(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        payload = self._success_payload(attempt)

        legacy_wallet = LegacyFinanceWalletService.get_or_create_wallet(party_id=self.party.id)
        balance_before = legacy_wallet.balance

        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference,
            payload=payload,
        )

        legacy_wallet.refresh_from_db()
        self.assertEqual(legacy_wallet.balance, balance_before)

    def test_callback_for_non_order_intent_does_not_create_finance_payment_transaction(self):
        assert self.intent.reference_type != "Order"
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        payload = self._success_payload(attempt)

        count_before = PaymentTransaction.objects.count()

        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference,
            payload=payload,
        )

        self.assertEqual(PaymentTransaction.objects.count(), count_before)
