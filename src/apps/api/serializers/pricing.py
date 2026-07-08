"""
DRF serializers for the Pricing quote endpoint — Module 17B.

Transport shape only. QuoteRequestSerializer validates types/presence;
every business rule (base-rule resolution, promotions, holiday/weekend
surcharges) stays inside apps.pricing.services.QuoteService.
"""

from rest_framework import serializers


class QuoteRequestSerializer(serializers.Serializer):
    service_category_id = serializers.UUIDField(required=False, allow_null=True)
    supplier_id = serializers.UUIDField(required=False, allow_null=True)
    order_id = serializers.UUIDField(required=False, allow_null=True)
    base_amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    duration_hours = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    currency = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(required=False)


class QuoteSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tenant_id = serializers.UUIDField()
    status = serializers.CharField()
    currency = serializers.CharField()
    base_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    surcharge_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    subtotal_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    created_at = serializers.DateTimeField()
