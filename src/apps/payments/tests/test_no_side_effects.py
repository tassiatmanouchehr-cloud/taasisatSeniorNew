"""
Proves apps.payments does not mutate Wallet or Finance settlement state on
a successful callback. Wallet crediting and finance.PaymentTransaction
creation are explicitly deferred to a future orchestration module.
"""

from decimal import Decimal

from apps.finance.models import PaymentTransaction
from apps.finance.services import WalletService as LegacyFinanceWalletService
from apps.payments.services import PaymentCallbackService, PaymentIntentService
from apps.wallet.models import Wallet, WalletTransaction

from .helpers import PaymentsTestCase


class PaymentNoSideEffectsTest(PaymentsTestCase):
    def test_successful_callback_does_not_touch_wallet_app(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        payload = self._success_payload(attempt)

        wallet_count_before = Wallet.objects.count()
        wallet_txn_count_before = WalletTransaction.objects.count()

        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference, payload=payload,
        )

        self.assertEqual(Wallet.objects.count(), wallet_count_before)
        self.assertEqual(WalletTransaction.objects.count(), wallet_txn_count_before)

    def test_successful_callback_does_not_touch_legacy_finance_wallet(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        payload = self._success_payload(attempt)

        legacy_wallet = LegacyFinanceWalletService.get_or_create_wallet(party_id=self.party.id)
        balance_before = legacy_wallet.balance

        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference, payload=payload,
        )

        legacy_wallet.refresh_from_db()
        self.assertEqual(legacy_wallet.balance, balance_before)

    def test_successful_callback_does_not_create_finance_payment_transaction(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        payload = self._success_payload(attempt)

        count_before = PaymentTransaction.objects.count()

        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference, payload=payload,
        )

        self.assertEqual(PaymentTransaction.objects.count(), count_before)
