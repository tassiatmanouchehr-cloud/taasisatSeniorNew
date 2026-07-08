"""
DiscoveryService — Module 12 foundation.

The single public entry point: normalize -> filter -> rank -> paginate.
Read-only end to end; never persists anything. This is the service-layer
stand-in for the (deliberately deferred) API endpoint.
"""

from .dto import SearchResultPage
from .query_normalizer import normalize_query
from .ranking_service import DiscoveryRankingService
from .search_service import SupplierSearchService


class DiscoveryService:
    """Orchestrates a full search: normalize, filter, rank, paginate."""

    @classmethod
    def search(
        cls,
        *,
        tenant_id,
        text="",
        service_category_id=None,
        supplier_type=None,
        availability_status=None,
        verification_level=None,
        city=None,
        requested_start=None,
        requested_end=None,
        limit=None,
        offset=0,
    ) -> SearchResultPage:
        query = normalize_query(
            tenant_id=tenant_id,
            text=text,
            service_category_id=service_category_id,
            supplier_type=supplier_type,
            availability_status=availability_status,
            verification_level=verification_level,
            city=city,
            requested_start=requested_start,
            requested_end=requested_end,
            limit=limit,
            offset=offset,
        )

        candidates = SupplierSearchService.filter_suppliers(query)
        ranked = DiscoveryRankingService.rank(tenant_id=tenant_id, suppliers=candidates)

        total_count = len(ranked)
        page_items = tuple(ranked[query.offset: query.offset + query.limit])

        return SearchResultPage(
            items=page_items, total_count=total_count, limit=query.limit, offset=query.offset,
        )
