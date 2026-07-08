"""
Base API view + sample endpoints — Module 17A foundation, DRF-based.

DRF's own dispatch() -> handle_exception() -> settings.REST_FRAMEWORK
["EXCEPTION_HANDLER"] (apps.api.exception_handler.api_exception_handler)
is what maps exceptions to the standard error envelope now — there is no
custom dispatch() override here. permission_classes = [AllowAny] on every
view is deliberate: apps.api.permissions.require_permission() performs the
real auth/tenant/RBAC enforcement manually (reusing PermissionService),
not DRF's own permission framework.
"""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reporting.services import OperationalReportService, ProviderReportService

from .pagination import paginate, parse_pagination_params
from .permissions import require_permission
from .serializers import OrderCountsReportSerializer, ProviderPerformanceReportSerializer


class ApiView(APIView):
    """Base class for all apps.api views."""

    permission_classes = [AllowAny]


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
