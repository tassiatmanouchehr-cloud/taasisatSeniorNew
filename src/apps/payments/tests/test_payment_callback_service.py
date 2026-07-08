from decimal import Decimal

from apps.payments.models import PaymentCallback, PaymentStatus
from apps.payments.services import PaymentCallbackService, PaymentError, PaymentIntentService

from .helpers import PaymentsTestCase


class PaymentCallbackServiceTest(PaymentsTestCase):
    def setUp(self):
        super().setUp()
        self.attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)

    def test_successful_callback_transitions_to_succeeded(self):
        payload = self._success_payload(self.attempt)

        result = PaymentCallbackService.process_callback(
            provider_reference=self.attempt.provider_reference, payload=payload,
        )

        self.assertEqual(result.status, PaymentStatus.SUCCEEDED)
        self.assertFalse(result.idempotent_replay)

        self.attempt.refresh_from_db()
        self.intent.refresh_from_db()
        self.assertEqual(self.attempt.status, PaymentStatus.SUCCEEDED)
        self.assertEqual(self.intent.status, PaymentStatus.SUCCEEDED)

        callback = PaymentCallback.objects.get(attempt=self.attempt, provider_event_id=payload["provider_event_id"])
        self.assertTrue(callback.accepted)
        self.assertEqual(callback.payload, payload)

    def test_failed_callback_transitions_to_failed(self):
        payload = self._success_payload(self.attempt, status="FAILED")

        result = PaymentCallbackService.process_callback(
            provider_reference=self.attempt.provider_reference, payload=payload,
        )

        self.assertEqual(result.status, PaymentStatus.FAILED)
        self.attempt.refresh_from_db()
        self.intent.refresh_from_db()
        self.assertEqual(self.attempt.status, PaymentStatus.FAILED)
        self.assertEqual(self.intent.status, PaymentStatus.FAILED)

    def test_duplicate_callback_is_idempotent(self):
        payload = self._success_payload(self.attempt)

        first = PaymentCallbackService.process_callback(
            provider_reference=self.attempt.provider_reference, payload=payload,
        )
        second = PaymentCallbackService.process_callback(
            provider_reference=self.attempt.provider_reference, payload=payload,
        )

        self.assertFalse(first.idempotent_replay)
        self.assertTrue(second.idempotent_replay)
        self.assertEqual(second.status, PaymentStatus.SUCCEEDED)

        self.assertEqual(
            PaymentCallback.objects.filter(attempt=self.attempt, provider_event_id=payload["provider_event_id"]).count(),
            1,
        )

    def test_callback_amount_mismatch_is_rejected(self):
        payload = self._success_payload(self.attempt, amount=Decimal("999999"))

        with self.assertRaises(PaymentError):
            PaymentCallbackService.process_callback(
                provider_reference=self.attempt.provider_reference, payload=payload,
            )

        self.attempt.refresh_from_db()
        self.intent.refresh_from_db()
        self.assertEqual(self.attempt.status, PaymentStatus.PENDING)
        self.assertEqual(self.intent.status, PaymentStatus.PENDING)

        callback = PaymentCallback.objects.get(attempt=self.attempt, provider_event_id=payload["provider_event_id"])
        self.assertFalse(callback.accepted)
        self.assertIn("Amount mismatch", callback.rejection_reason)

    def test_callback_currency_mismatch_is_rejected(self):
        payload = self._success_payload(self.attempt, currency="USD")

        with self.assertRaises(PaymentError):
            PaymentCallbackService.process_callback(
                provider_reference=self.attempt.provider_reference, payload=payload,
            )

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, PaymentStatus.PENDING)

        callback = PaymentCallback.objects.get(attempt=self.attempt, provider_event_id=payload["provider_event_id"])
        self.assertFalse(callback.accepted)
        self.assertIn("Currency mismatch", callback.rejection_reason)

    def test_invalid_state_transition_is_rejected(self):
        payload = self._success_payload(self.attempt, status="SUCCEEDED")
        PaymentCallbackService.process_callback(provider_reference=self.attempt.provider_reference, payload=payload)

        # A second, DIFFERENT event trying to move an already-terminal attempt is invalid.
        second_payload = self._success_payload(self.attempt, status="FAILED")
        with self.assertRaises(PaymentError):
            PaymentCallbackService.process_callback(
                provider_reference=self.attempt.provider_reference, payload=second_payload,
            )

        callback = PaymentCallback.objects.get(
            attempt=self.attempt, provider_event_id=second_payload["provider_event_id"],
        )
        self.assertFalse(callback.accepted)
        self.assertIn("Invalid payment state transition", callback.rejection_reason)

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, PaymentStatus.SUCCEEDED)

    def test_callback_for_unknown_provider_reference_raises(self):
        with self.assertRaises(PaymentError):
            PaymentCallbackService.process_callback(
                provider_reference="FAKE-does-not-exist",
                payload={
                    "provider_reference": "FAKE-does-not-exist",
                    "provider_event_id": "evt-x",
                    "status": "SUCCEEDED",
                    "amount": "100000",
                    "currency": "IRR",
                },
            )

    def test_malformed_payload_is_rejected(self):
        with self.assertRaises(PaymentError):
            PaymentCallbackService.process_callback(
                provider_reference=self.attempt.provider_reference,
                payload={"provider_reference": self.attempt.provider_reference},
            )

    def test_payload_snapshot_is_persisted_verbatim(self):
        payload = self._success_payload(self.attempt, status="AUTHORIZED")

        PaymentCallbackService.process_callback(
            provider_reference=self.attempt.provider_reference, payload=payload,
        )

        callback = PaymentCallback.objects.get(attempt=self.attempt, provider_event_id=payload["provider_event_id"])
        self.assertEqual(callback.payload, payload)
        self.assertEqual(callback.resulting_status, PaymentStatus.AUTHORIZED)

    def test_provider_reference_persists_on_attempt(self):
        self.assertTrue(self.attempt.provider_reference)
        persisted = self.attempt.__class__.objects.get(id=self.attempt.id)
        self.assertEqual(persisted.provider_reference, self.attempt.provider_reference)
