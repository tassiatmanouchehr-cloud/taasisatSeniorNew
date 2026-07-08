"""
FakePaymentProviderAdapter — Module 15 foundation.

The only provider adapter implemented in this module. Pure in-memory,
deterministic, no network calls. Real PSP adapters (Zarinpal, Mellat,
Stripe, ...) are deferred entirely.
"""

import uuid
from decimal import Decimal

from ..models import PaymentProvider


class FakePaymentProviderAdapter:
    """Models request_payment() / verify_callback() without calling any external network."""

    provider = PaymentProvider.FAKE

    @classmethod
    def request_payment(cls, *, amount: Decimal, currency: str, metadata: dict | None = None) -> dict:
        """Simulates asking the provider to start collecting a payment."""
        provider_reference = f"FAKE-{uuid.uuid4().hex[:20]}"
        return {
            "provider_reference": provider_reference,
            "request_snapshot": {
                "amount": str(amount),
                "currency": currency,
                "metadata": metadata or {},
            },
            "response_snapshot": {
                "provider_reference": provider_reference,
                "status": "PENDING",
            },
        }

    @classmethod
    def verify_callback(cls, payload: dict) -> dict:
        """Normalizes a raw callback payload into the canonical shape the service layer expects.

        A real adapter would verify a signature/HMAC here; the fake adapter only checks structure.
        """
        required_fields = ("provider_reference", "provider_event_id", "status", "amount", "currency")
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"Callback payload missing required field(s): {missing}")

        return {
            "provider_reference": payload["provider_reference"],
            "provider_event_id": payload["provider_event_id"],
            "status": payload["status"],
            "amount": payload["amount"],
            "currency": payload["currency"],
        }
