"""DRF serializers for apps.reporting DTOs — Module 17A. Transport shape only."""

from rest_framework import serializers


class OrderCountsReportSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    total_orders = serializers.IntegerField()
    active_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())


class ProviderPerformanceReportSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    supplier_id = serializers.UUIDField()
    completed_services = serializers.IntegerField()
    reputation_average = serializers.DecimalField(max_digits=3, decimal_places=2, allow_null=True)
    reputation_review_count = serializers.IntegerField()
    availability_status = serializers.CharField()
    total_assignments = serializers.IntegerField()
    active_assignments = serializers.IntegerField()
