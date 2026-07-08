"""
DRF serializers for the Payments endpoints — Module 17B.

Transport shape only. Idempotency, state-machine validation, and
amount/currency verification against the original intent all stay inside
apps.payments.services.
"""

from rest_framework import serializers


class PaymentIntentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    idempotency_key = serializers.CharField()
    currency = serializers.CharField(required=False, allow_blank=True)
    reference_type = serializers.CharField(required=False, allow_blank=True)
    reference_id = serializers.UUIDField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False)


class PaymentIntentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
    provider = serializers.CharField()
    expires_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class PaymentAttemptSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    provider = serializers.CharField()
    provider_reference = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()


class FakeCallbackSerializer(serializers.Serializer):
    provider_reference = serializers.CharField()
    provider_event_id = serializers.CharField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
