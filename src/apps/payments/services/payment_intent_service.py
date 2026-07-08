"""
PaymentIntentService — Module 15 foundation.

Creates PaymentIntent rows (idempotent per tenant + idempotency_key) and
starts PaymentAttempts against the registered provider adapter. Intent
creation and attempt-starting are the only code that mutates PaymentIntent.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import DEFAULT_CURRENCY, PaymentAttempt, PaymentIntent, PaymentProvider, PaymentStatus
from .configuration import PaymentConfiguration
from .errors import PaymentError
from .provider_registry import PaymentProviderRegistry
from .transitions import is_transition_allowed

QUANT = Decimal("0.01")


def _q(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)


class PaymentIntentService:
    """Creates PaymentIntent rows and starts provider-facing PaymentAttempts."""

    @classmethod
    @transaction.atomic
    def create_intent(
        cls, *, payer_party, amount, idempotency_key,
        currency=None, provider=None, reference_type="", reference_id=None, metadata=None,
    ) -> PaymentIntent:
        if amount is None or _q(amount) <= 0:
            raise PaymentError("Payment amount must be positive.")

        currency = currency or DEFAULT_CURRENCY
        if not isinstance(currency, str) or not currency.strip():
            raise PaymentError("Payment currency must be a non-empty string.")

        if not idempotency_key:
            raise PaymentError("idempotency_key is required to create a PaymentIntent.")

        tenant_id = payer_party.tenant_id
        provider = provider or PaymentConfiguration.get_default_provider(tenant_id=tenant_id)
        if provider not in PaymentProvider.values:
            raise PaymentError(f"Unknown payment provider: {provider}")

        existing = PaymentIntent.objects.filter(tenant_id=tenant_id, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing

        expiry_seconds = PaymentConfiguration.get_intent_expiry_seconds(tenant_id=tenant_id)

        try:
            with transaction.atomic():
                intent = PaymentIntent.objects.create(
                    tenant_id=tenant_id,
                    payer_party=payer_party,
                    amount=_q(amount),
                    currency=currency,
                    provider=provider,
                    status=PaymentStatus.CREATED,
                    idempotency_key=idempotency_key,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    expires_at=timezone.now() + timedelta(seconds=expiry_seconds),
                    metadata=metadata or {},
                )
        except IntegrityError:
            existing = PaymentIntent.objects.filter(tenant_id=tenant_id, idempotency_key=idempotency_key).first()
            if existing is not None:
                return existing
            raise

        return intent

    @classmethod
    @transaction.atomic
    def start_attempt(cls, *, intent_id) -> PaymentAttempt:
        intent = PaymentIntent.objects.select_for_update().get(id=intent_id)

        if not is_transition_allowed(intent.status, PaymentStatus.PENDING):
            raise PaymentError(
                f"Cannot start a payment attempt: intent is in '{intent.status}' status.",
            )

        adapter = PaymentProviderRegistry.get_adapter(intent.provider)
        result = adapter.request_payment(amount=intent.amount, currency=intent.currency, metadata=intent.metadata)

        attempt = PaymentAttempt.objects.create(
            tenant_id=intent.tenant_id,
            intent=intent,
            provider=intent.provider,
            provider_reference=result["provider_reference"],
            status=PaymentStatus.PENDING,
            request_snapshot=result["request_snapshot"],
            response_snapshot=result["response_snapshot"],
        )

        intent.status = PaymentStatus.PENDING
        intent.save(update_fields=["status", "updated_at"])

        return attempt
