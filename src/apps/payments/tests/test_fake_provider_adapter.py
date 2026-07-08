from decimal import Decimal

from django.test import TestCase

from apps.payments.providers.fake import FakePaymentProviderAdapter


class FakePaymentProviderAdapterTest(TestCase):
    def test_request_payment_returns_provider_reference_and_snapshots(self):
        result = FakePaymentProviderAdapter.request_payment(amount=Decimal("1000"), currency="IRR")

        self.assertTrue(result["provider_reference"].startswith("FAKE-"))
        self.assertEqual(result["request_snapshot"]["amount"], "1000")
        self.assertEqual(result["request_snapshot"]["currency"], "IRR")
        self.assertEqual(result["response_snapshot"]["provider_reference"], result["provider_reference"])

    def test_request_payment_generates_unique_references(self):
        first = FakePaymentProviderAdapter.request_payment(amount=Decimal("1000"), currency="IRR")
        second = FakePaymentProviderAdapter.request_payment(amount=Decimal("1000"), currency="IRR")

        self.assertNotEqual(first["provider_reference"], second["provider_reference"])

    def test_verify_callback_normalizes_valid_payload(self):
        payload = {
            "provider_reference": "FAKE-abc",
            "provider_event_id": "evt-1",
            "status": "SUCCEEDED",
            "amount": "1000",
            "currency": "IRR",
        }

        normalized = FakePaymentProviderAdapter.verify_callback(payload)

        self.assertEqual(normalized, payload)

    def test_verify_callback_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            FakePaymentProviderAdapter.verify_callback({"provider_reference": "FAKE-abc"})

    def test_verify_callback_does_not_call_network(self):
        # No network client is imported/used anywhere in the adapter module.
        import apps.payments.providers.fake as fake_module

        source = open(fake_module.__file__).read()
        for forbidden in ("requests", "httpx", "urllib", "socket"):
            self.assertNotIn(forbidden, source)
