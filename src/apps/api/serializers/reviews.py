"""
DRF serializers for the Reviews endpoints — Module 17B.

Transport shape only. Rating bounds, duplicate/completed-order checks,
and moderation status all stay inside apps.reviews.services.
"""

from rest_framework import serializers


class ReviewSubmitSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    dimension_scores = serializers.DictField(child=serializers.IntegerField())
    written_text = serializers.CharField(required=False, allow_blank=True)


class ReviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_id = serializers.UUIDField(allow_null=True)
    supplier_id = serializers.UUIDField()
    moderation_status = serializers.CharField()
    overall_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    written_text = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class ReputationSummarySerializer(serializers.Serializer):
    review_count = serializers.IntegerField()
    average_score = serializers.DecimalField(max_digits=3, decimal_places=2, allow_null=True)
