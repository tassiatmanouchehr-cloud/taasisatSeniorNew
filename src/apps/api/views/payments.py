"""
Payments endpoints — Module 17B.

payer_party always comes from the authenticated user's own CustomerProfile
— never accepted from the request body, so one user can never create a
payment intent as another. The fake-callback endpoint is deliberately
unauthenticated: it simulates an external PSP webhook, which in
production carries no Django session at all — see apps/api/views/payments.py
module docstring in the Module 17B architecture report for the full
rationale. It is hard-restricted to PaymentProvider.FAKE attempts only.
"""

from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from apps.finance.services import FinancialPartyService
from apps.payments.models import PaymentAttempt, PaymentIntent, PaymentProvider
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from ..errors import ApiError
from ..permission_keys import PAYMENTS_ATTEMPTS_CREATE, PAYMENTS_INTENTS_CREATE
from ..permissions import require_permission, resolve_customer_profile
from ..serializers import (
    FakeCallbackSerializer,
    PaymentAttemptSerializer,
    PaymentIntentCreateSerializer,
    PaymentIntentSerializer,
)
from .base import ApiView


class PaymentIntentCreateView(ApiView):
    """POST /api/v1/payments/intents/ — idempotent PaymentIntent creation."""

    def post(self, request):
        tenant_id = require_permission(request, PAYMENTS_INTENTS_CREATE)
        customer_profile = resolve_customer_profile(request)

        payload = PaymentIntentCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        payer_party = FinancialPartyService.resolve_party_for_customer(customer_profile)

        intent = PaymentIntentService.create_intent(
            payer_party=payer_party,
            amount=data["amount"],
            idempotency_key=data["idempotency_key"],
            currency=data.get("currency") or None,
            reference_type=data.get("reference_type", ""),
            reference_id=data.get("reference_id"),
            metadata=data.get("metadata"),
        )

        # tenant_id is available via payer_party.tenant_id == tenant_id (enforced by FinancialParty lookup).
        return Response(PaymentIntentSerializer(intent).data, status=HTTP_201_CREATED)


class PaymentAttemptCreateView(ApiView):
    """POST /api/v1/payments/intents/{intent_id}/attempts/ — starts a provider attempt."""

    def post(self, request, intent_id):
        tenant_id = require_permission(request, PAYMENTS_ATTEMPTS_CREATE)

        # Tenant-scoped lookup first: never let start_attempt() run against another tenant's intent.
        PaymentIntent.objects.get(id=intent_id, tenant_id=tenant_id)

        attempt = PaymentIntentService.start_attempt(intent_id=intent_id)
        return Response(PaymentAttemptSerializer(attempt).data, status=HTTP_201_CREATED)


class FakeProviderCallbackView(ApiView):
    """
    POST /api/v1/payments/callbacks/fake/ — test/fake provider callback only.

    Deliberately unauthenticated (mirrors a real PSP webhook). Scoped by
    knowledge of the unguessable provider_reference token, and hard-limited
    to PaymentProvider.FAKE attempts. Real PSP signature/HMAC verification
    is out of scope and deferred.
    """

    def post(self, request):
        payload = FakeCallbackSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        provider_reference = data["provider_reference"]

        try:
            attempt = PaymentAttempt.objects.get(provider_reference=provider_reference)
        except PaymentAttempt.DoesNotExist:
            raise ApiError(code="not_found", message="No payment attempt found for that provider_reference.", status_code=404)

        if attempt.provider != PaymentProvider.FAKE:
            raise ApiError(
                code="unsupported_provider",
                message="This endpoint only accepts callbacks for the fake provider.",
                status_code=400,
            )

        result = PaymentCallbackService.process_callback(
            provider_reference=provider_reference,
            payload={
                "provider_reference": provider_reference,
                "provider_event_id": data["provider_event_id"],
                "status": data["status"],
                "amount": str(data["amount"]),
                "currency": data["currency"],
            },
        )

        return Response({
            "intent_id": str(result.intent_id),
            "attempt_id": str(result.attempt_id) if result.attempt_id else None,
            "status": result.status,
            "idempotent_replay": result.idempotent_replay,
        })
