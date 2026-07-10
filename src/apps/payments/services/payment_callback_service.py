"""
PaymentCallbackService — Module 15 foundation.

Processes provider callbacks idempotently. Never trusts callback
amount/currency without validating against the original PaymentIntent.
Every callback — accepted or rejected — is durably logged as a
PaymentCallback row *before* any error is raised to the caller: the
`with transaction.atomic()` block below is deliberately not a decorator on
the whole method, so a rejection's audit row commits even though the
method then raises PaymentError.

Sprint 1 (Epic 03, Financial Settlement): once the callback's own atomic
block has committed and the intent has genuinely (not a replay) reached
SUCCEEDED, this triggers SettlementOrchestrationService to connect the
payment to the finance/wallet money flow. Settlement failures are logged,
never re-raised — the callback's own durability guarantee (the provider
gets a definitive accept/reject) must stay independent of settlement
succeeding.

Remediation (Architecture Review, Critical Finding 1): a synchronous
settlement failure is no longer just a log line — it also enqueues a
durable, idempotent `payments.settlement.retry` job (apps.jobs) so the
PaymentIntent is never silently left SUCCEEDED with no recovery path. See
apps.payments.jobs for the handler and DECISION_HISTORY.md for why
apps.jobs (not a new mechanism) was reused.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from apps.jobs.services.job_service import JobService

from ..jobs import PAYMENT_SETTLEMENT_RETRY
from ..models import PaymentAttempt, PaymentCallback, PaymentIntent, PaymentStatus
from .dto import PaymentResult
from .errors import PaymentError
from .provider_registry import PaymentProviderRegistry
from .settlement_orchestration_service import SettlementOrchestrationService
from .transitions import is_transition_allowed

logger = logging.getLogger(__name__)

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

        if intent.status == PaymentStatus.SUCCEEDED:
            cls._trigger_settlement(intent)

        return PaymentResult(
            intent_id=intent.id, attempt_id=attempt.id, status=intent.status,
            amount=intent.amount, currency=intent.currency,
            provider_reference=attempt.provider_reference, message="Callback processed.",
        )

    @staticmethod
    def _trigger_settlement(intent: PaymentIntent) -> None:
        """Best-effort: a settlement failure must never undo an already-accepted callback.

        Never re-raised — the callback's own accept/reject guarantee stays
        independent of settlement succeeding. On failure, durably enqueues a
        `payments.settlement.retry` job instead of relying on a log line as
        the only recovery signal (Architecture Review, Critical Finding 1).
        JobService.enqueue() is idempotent per (tenant_id, job_type,
        idempotency_key) — a database-unique constraint, not a read-then-
        write check — so calling this from multiple failed attempts for the
        same intent never creates more than one retry job.
        """
        try:
            SettlementOrchestrationService.settle_payment_intent(payment_intent_id=intent.id)
        except Exception:
            logger.exception(
                "Settlement orchestration failed for PaymentIntent %s; callback acceptance stands. "
                "Enqueuing payments.settlement.retry for recovery.",
                intent.id,
            )
            JobService.enqueue(
                job_type=PAYMENT_SETTLEMENT_RETRY,
                idempotency_key=str(intent.id),
                tenant_id=intent.tenant_id,
                payload={"payment_intent_id": str(intent.id)},
            )
