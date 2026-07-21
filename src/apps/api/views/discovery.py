"""Discovery endpoint — Module 17B. Read-only, calls DiscoveryService end to end."""

from rest_framework.response import Response

from apps.discovery.services import DiscoveryService

from ..pagination import parse_pagination_params
from ..permission_keys import DISCOVERY_SUPPLIERS_READ
from ..permissions import require_permission
from ..serializers import SearchResultItemSerializer
from .base import ApiView


class SupplierDiscoveryListView(ApiView):
    """GET /api/v1/discovery/suppliers/ — filterable, paginated, read-only supplier search."""

    def get(self, request):
        tenant_id = require_permission(request, DISCOVERY_SUPPLIERS_READ)
        limit, offset = parse_pagination_params(request.query_params)

        page = DiscoveryService.search(
            tenant_id=tenant_id,
            text=request.query_params.get("text", ""),
            service_category_id=request.query_params.get("service_category_id") or None,
            supplier_type=request.query_params.get("supplier_type") or None,
            availability_status=request.query_params.get("availability_status") or None,
            verification_level=request.query_params.get("verification_level") or None,
            city=request.query_params.get("city") or None,
            limit=limit,
            offset=offset,
        )

        serializer = SearchResultItemSerializer(page.items, many=True)
        return Response(
            {
                "results": serializer.data,
                "limit": page.limit,
                "offset": page.offset,
                "total_count": page.total_count,
                "has_more": (page.offset + page.limit) < page.total_count,
            }
        )
