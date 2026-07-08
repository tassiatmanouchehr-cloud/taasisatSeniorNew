"""Discovery services — Search, Discovery & Provider Ranking (Module 12)."""

from .configuration import DiscoveryConfiguration
from .discovery_service import DiscoveryService
from .dto import SearchQuery, SearchResultItem, SearchResultPage
from .errors import DiscoveryError
from .query_normalizer import normalize_query
from .ranking_service import DiscoveryRankingService
from .search_service import SupplierSearchService

__all__ = [
    "DiscoveryError",
    "DiscoveryConfiguration",
    "SearchQuery",
    "SearchResultItem",
    "SearchResultPage",
    "normalize_query",
    "SupplierSearchService",
    "DiscoveryRankingService",
    "DiscoveryService",
]
