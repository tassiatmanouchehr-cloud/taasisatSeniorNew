from decimal import Decimal

from apps.payments.models import PaymentAttempt, PaymentIntent, PaymentProvider, PaymentStatus
from apps.payments.services import PaymentError, PaymentIntentService

from .helpers import PaymentsTestCase


class PaymentIntentServiceTest(PaymentsTestCase):
    def test_create_intent_defaults(self):
        self.assertEqual(self.intent.amount, Decimal("100000.00"))
        self.assertEqual(self.intent.currency, "IRR")
        self.assertEqual(self.intent.provider, PaymentProvider.FAKE)
        self.assertEqual(self.intent.status, PaymentStatus.CREATED)
        self.assertEqual(self.intent.tenant_id, self.tenant.id)
        self.assertIsNotNone(self.intent.expires_at)

    def test_create_intent_is_idempotent(self):
        key = "shared-idem-key"
        first = PaymentIntentService.create_intent(
            payer_party=self.party,
            amount=Decimal("5000"),
            idempotency_key=key,
        )
        second = PaymentIntentService.create_intent(
            payer_party=self.party,
            amount=Decimal("5000"),
            idempotency_key=key,
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(PaymentIntent.objects.filter(idempotency_key=key).count(), 1)

    def test_create_intent_rejects_zero_or_negative_amount(self):
        with self.assertRaises(PaymentError):
            PaymentIntentService.create_intent(
                payer_party=self.party,
                amount=Decimal("0"),
                idempotency_key="zero-amount",
            )

        with self.assertRaises(PaymentError):
            PaymentIntentService.create_intent(
                payer_party=self.party,
                amount=Decimal("-10"),
                idempotency_key="negative-amount",
            )

    def test_create_intent_rejects_empty_currency(self):
        with self.assertRaises(PaymentError):
            PaymentIntentService.create_intent(
                payer_party=self.party,
                amount=Decimal("100"),
                idempotency_key="empty-currency",
                currency="   ",
            )

    def test_create_intent_requires_idempotency_key(self):
        with self.assertRaises(PaymentError):
            PaymentIntentService.create_intent(
                payer_party=self.party,
                amount=Decimal("100"),
                idempotency_key="",
            )

    def test_create_intent_rejects_unknown_provider(self):
        with self.assertRaises(PaymentError):
            PaymentIntentService.create_intent(
                payer_party=self.party,
                amount=Decimal("100"),
                idempotency_key="bad-provider",
                provider="STRIPE",
            )

    def test_start_attempt_creates_attempt_and_transitions_intent(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)

        self.assertEqual(attempt.status, PaymentStatus.PENDING)
        self.assertTrue(attempt.provider_reference.startswith("FAKE-"))
        self.assertEqual(attempt.tenant_id, self.tenant.id)

        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentStatus.PENDING)

    def test_start_attempt_rejects_when_not_created(self):
        PaymentIntentService.start_attempt(intent_id=self.intent.id)

        with self.assertRaises(PaymentError):
            PaymentIntentService.start_attempt(intent_id=self.intent.id)

    def test_start_attempt_persists_request_and_response_snapshots(self):
        attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)

        self.assertIn("amount", attempt.request_snapshot)
        self.assertIn("provider_reference", attempt.response_snapshot)

        persisted = PaymentAttempt.objects.get(id=attempt.id)
        self.assertEqual(persisted.request_snapshot, attempt.request_snapshot)
        self.assertEqual(persisted.response_snapshot, attempt.response_snapshot)
