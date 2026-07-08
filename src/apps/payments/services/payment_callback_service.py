"""
PaymentCallbackService — Module 15 foundation.

Processes provider callbacks idempotently. Never trusts callback
amount/currency without validating against the original PaymentIntent.
Every callback — accepted or rejected — is durably logged as a
PaymentCallback row *before* any error is raised to the caller: the
`with transaction.atomic()` block below is deliberately not a decorator on
the whole method, so a rejection's audit row commits even though the
method then raises PaymentError.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from ..models import PaymentAttempt, PaymentCallback, PaymentIntent, PaymentStatus
from .dto import PaymentResult
from .errors import PaymentError
from .provider_registry import PaymentProviderRegistry
from .transitions import is_transition_allowed

QUANT = Decimal("0.01")


def _q(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)


class PaymentCallbackService:
    """Validates and applies a single provider callback against its PaymentAttempt/PaymentIntent."""

    @classmethod
    def process_callback(cls, *, provider_reference: str, payload: dict) -> PaymentResult:
        rejection_reason = None

        with transaction.atomic():
            try:
                attempt = PaymentAttempt.objects.select_for_update().get(provider_reference=provider_reference)
            except PaymentAttempt.DoesNotExist as exc:
                raise PaymentError(
                    f"No payment attempt found for provider_reference '{provider_reference}'.",
                ) from exc

            intent = PaymentIntent.objects.select_for_update().get(id=attempt.intent_id)

            adapter = PaymentProviderRegistry.get_adapter(attempt.provider)
            try:
                normalized = adapter.verify_callback(payload)
            except ValueError as exc:
                raise PaymentError(str(exc)) from exc

            provider_event_id = normalized["provider_event_id"]

            existing_callback = PaymentCallback.objects.filter(
                attempt=attempt, provider_event_id=provider_event_id,
            ).first()
            if existing_callback is not None:
                return PaymentResult(
                    intent_id=intent.id, attempt_id=attempt.id, status=intent.status,
                    amount=intent.amount, currency=intent.currency,
                    provider_reference=attempt.provider_reference,
                    idempotent_replay=True, message="Callback already processed.",
                )

            callback_amount = _q(normalized["amount"])
            target_status = normalized["status"]

            if callback_amount != intent.amount:
                rejection_reason = (
                    f"Amount mismatch: callback={callback_amount} intent={intent.amount}"
                )
            elif normalized["currency"] != intent.currency:
                rejection_reason = (
                    f"Currency mismatch: callback={normalized['currency']} intent={intent.currency}"
                )
            elif target_status not in PaymentStatus.values:
                rejection_reason = f"Unknown status in callback: {target_status}"
            elif not is_transition_allowed(attempt.status, target_status):
                rejection_reason = (
                    f"Invalid payment state transition: {attempt.status} -> {target_status}"
                )

            if rejection_reason:
                PaymentCallback.objects.create(
                    tenant_id=attempt.tenant_id, attempt=attempt, provider_event_id=provider_event_id,
                    payload=payload, accepted=False, rejection_reason=rejection_reason,
                )
            else:
                PaymentCallback.objects.create(
                    tenant_id=attempt.tenant_id, attempt=attempt, provider_event_id=provider_event_id,
                    payload=payload, accepted=True, resulting_status=target_status,
                )
                attempt.status = target_status
                attempt.save(update_fields=["status", "updated_at"])
                intent.status = target_status
                intent.save(update_fields=["status", "updated_at"])

        # The atomic block above has committed by this point (in either branch).
        if rejection_reason:
            raise PaymentError(rejection_reason)

        intent.refresh_from_db()
        attempt.refresh_from_db()
        return PaymentResult(
            intent_id=intent.id, attempt_id=attempt.id, status=intent.status,
            amount=intent.amount, currency=intent.currency,
            provider_reference=attempt.provider_reference, message="Callback processed.",
        )
