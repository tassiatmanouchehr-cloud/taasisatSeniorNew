"""Reporting sample endpoints — Module 17A foundation (unchanged in Module 17B)."""

from rest_framework.response import Response

from apps.reporting.services import OperationalReportService, ProviderReportService

from ..pagination import paginate, parse_pagination_params
from ..permissions import require_permission
from ..serializers import OrderCountsReportSerializer, ProviderPerformanceReportSerializer
from .base import ApiView


class OrderCountsSampleView(ApiView):
    """GET /api/v1/sample/order-counts/ — authenticated + RBAC-guarded read-only sample."""

    def get(self, request):
        tenant_id = require_permission(request, "reporting.read")
        report = OperationalReportService.get_order_counts(tenant_id)
        serializer = OrderCountsReportSerializer(report)
        return Response(serializer.data)


class ProviderReportsSampleView(ApiView):
    """GET /api/v1/sample/providers/ — authenticated + RBAC-guarded, demonstrates pagination."""

    def get(self, request):
        tenant_id = require_permission(request, "reporting.read")
        limit, offset = parse_pagination_params(request.query_params)
        reports = ProviderReportService.list_reports(tenant_id)
        page = paginate(reports, limit=limit, offset=offset)
        serializer = ProviderPerformanceReportSerializer(page.results, many=True)
        return Response({
            "results": serializer.data,
            "limit": page.limit,
            "offset": page.offset,
            "total_count": page.total_count,
            "has_more": page.has_more,
        })
