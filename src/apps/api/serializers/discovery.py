"""DRF serializers for apps.discovery DTOs — Module 17B. Transport shape only."""

from rest_framework import serializers


class SearchResultItemSerializer(serializers.Serializer):
    supplier_id = serializers.UUIDField()
    display_name = serializers.CharField()
    supplier_type = serializers.CharField()
    availability_status = serializers.CharField()
    verification_level = serializers.CharField()
    score = serializers.DecimalField(max_digits=12, decimal_places=6)
    score_breakdown = serializers.DictField()
