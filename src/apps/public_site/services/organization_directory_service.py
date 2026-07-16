"""
OrganizationDirectoryService — Phase 3 Sprint 3.3 (Company Public
Directory and Discovery).

Builds the public Organization Directory page, mirroring
apps.public_site.services.directory_service.CaregiverDirectoryService's
own architecture exactly: reuses apps.discovery's existing search/ranking
building blocks (SupplierSearchService.filter_suppliers() +
DiscoveryRankingService.rank()) and apps.public_site.services.common's
canonical bulk-resolution/visibility helpers unchanged — nothing here is
a second implementation of search, ranking, or visibility policy. See
traceability/ARCHITECTURE_DECISION_LOG.md ADM-025 for the full reasoning.

Scoped to SupplierType.ORGANIZATION only — the plain "company" supplier
type, distinct from CaregiverDirectoryService's own CAREGIVER_SUPPLIER_TYPES
(INDEPENDENT_PROVIDER / ORGANIZATION_PROVIDER), so the two directories
never overlap.

search()'s signature is deliberately kept parallel to
CaregiverDirectoryService.search()'s own (tenant_id, text, city,
service_category_id, page, base_url), omitting only the two caregiver-only
params (supplier_type, availability_status) — structural consistency only,
no abstract base class or SupplierDirectoryService is introduced here (out
of scope this sprint); a future Supplier-level discovery layer could
compose both directories without either needing to change shape first.
"""

import math

from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.accounts.services.supplier_bridge import resolve_supplier_entities_bulk
from apps.discovery.services.query_normalizer import normalize_query
from apps.discovery.services.ranking_service import DiscoveryRankingService
from apps.discovery.services.search_service import SupplierSearchService
from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.services.tenant_service import TenantService
from apps.orders.services.queries import CatalogQueryService

from . import common
from .viewmodels import (
    FilterOptionViewModel,
    OrganizationCardViewModel,
    OrganizationDirectoryFiltersViewModel,
    OrganizationDirectoryPageViewModel,
    RatingSummaryViewModel,
)

PAGE_SIZE = 12


class OrganizationDirectoryService:
    """Read-only: search + filter + paginate the public organization directory."""

    @classmethod
    def search(
        cls,
        *,
        tenant_id=None,
        text="",
        city=None,
        service_category_id=None,
        page=1,
        base_url="/find-an-organization/",
    ) -> OrganizationDirectoryPageViewModel:
        tenant_id = tenant_id or TenantService.get_default_tenant_id()

        candidates, attrs_by_id = cls._filter_candidates(
            tenant_id=tenant_id, text=text, city=city, service_category_id=service_category_id,
        )
        candidates_by_id = {supplier.id: supplier for supplier in candidates}
        ranked = DiscoveryRankingService.rank(tenant_id=tenant_id, suppliers=candidates)

        # Fetched once per search() call (never per card) — reused by both
        # _build_filters() (service_options) and _build_card()
        # (service_names), the same KL-012-avoidance shape as every other
        # bulk lookup in this class.
        categories = tuple(CatalogQueryService.list_active_categories(tenant_id=tenant_id).order_by("sort_order", "name"))

        total_count = len(ranked)
        total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
        current_page = max(1, min(common.parse_page(page), total_pages))
        offset = (current_page - 1) * PAGE_SIZE
        page_items = ranked[offset : offset + PAGE_SIZE]
        page_supplier_ids = [item.supplier_id for item in page_items if item.supplier_id in candidates_by_id]

        card_data = cls._bulk_card_data(
            suppliers=[candidates_by_id[supplier_id] for supplier_id in page_supplier_ids], categories=categories,
        )
        cards = tuple(
            cls._build_card(candidates_by_id[supplier_id], attrs_by_id[supplier_id], card_data=card_data)
            for supplier_id in page_supplier_ids
        )

        filters = cls._build_filters(
            tenant_id=tenant_id, text=text, city=city, service_category_id=service_category_id, categories=categories,
        )

        params = {}
        if text:
            params["q"] = text
        if city:
            params["city"] = city
        if service_category_id:
            params["service"] = str(service_category_id)

        pagination = common.build_pagination(
            current_page=current_page,
            total_pages=total_pages,
            total_count=total_count,
            base_url=base_url,
            params=params,
        )

        return OrganizationDirectoryPageViewModel(organizations=cards, filters=filters, pagination=pagination)

    @classmethod
    def available_cities(cls, *, tenant_id=None) -> tuple[str, ...]:
        """Distinct cities among all currently active, publicly-visible
        organizations — used to populate the city selector, unaffected by
        any active filter (mirrors CaregiverDirectoryService.available_cities())."""
        tenant_id = tenant_id or TenantService.get_default_tenant_id()
        _candidates, attrs_by_id = cls._filter_candidates(
            tenant_id=tenant_id, text="", city=None, service_category_id=None,
        )
        return common.distinct_cities_from_attrs(attrs_by_id.values())

    @classmethod
    def build_cards_for_supplier_ids(cls, supplier_ids, *, tenant_id=None) -> dict:
        """Phase 4 Sprint 4.1 (Customer Favorites): resolves an explicit,
        caller-chosen set of supplier ids into cards — the organization-side
        sibling of `CaregiverDirectoryService.build_cards_for_supplier_ids()`,
        same reasoning: reuses `_bulk_card_data()`/`_build_card()` unchanged,
        no second card-building implementation. Returns
        {supplier_id: OrganizationCardViewModel}, silently omitting any id
        that is not currently publicly visible."""
        tenant_id = tenant_id or TenantService.get_default_tenant_id()
        if not supplier_ids:
            return {}

        suppliers = list(
            ServiceSupplier.objects.filter(
                id__in=supplier_ids, tenant_id=tenant_id, status=SupplierStatus.ACTIVE,
                supplier_type=SupplierType.ORGANIZATION,
            ),
        )
        attrs_by_id = common.bulk_supplier_attrs(suppliers)
        eligible = [supplier for supplier in suppliers if common.is_publicly_visible_attrs(attrs_by_id[supplier.id])]

        categories = tuple(CatalogQueryService.list_active_categories(tenant_id=tenant_id).order_by("sort_order", "name"))
        card_data = cls._bulk_card_data(suppliers=eligible, categories=categories)
        return {
            supplier.id: cls._build_card(supplier, attrs_by_id[supplier.id], card_data=card_data)
            for supplier in eligible
        }

    # ------------------------------------------------------------------

    @classmethod
    def _filter_candidates(cls, *, tenant_id, text, city, service_category_id):
        """Returns (eligible_suppliers, attrs_by_id) — attrs_by_id covers
        every eligible supplier and is computed via exactly one batched
        resolution pass (common.bulk_supplier_attrs()), mirroring
        CaregiverDirectoryService._filter_candidates()'s own KL-012-hardened
        shape."""
        query = normalize_query(
            tenant_id=tenant_id,
            text=text,
            service_category_id=service_category_id,
            supplier_type=SupplierType.ORGANIZATION,
            availability_status=None,
            city=city,
        )
        candidates = list(SupplierSearchService.filter_suppliers(query))

        attrs_by_id = common.bulk_supplier_attrs(candidates)
        eligible = [supplier for supplier in candidates if common.is_publicly_visible_attrs(attrs_by_id[supplier.id])]
        return eligible, {supplier.id: attrs_by_id[supplier.id] for supplier in eligible}

    @staticmethod
    def _bulk_card_data(*, suppliers, categories) -> dict:
        """Precomputes, in a small fixed number of queries regardless of
        how many suppliers are passed, every per-card value that would
        otherwise cost one query per card — rating, the resolved
        OrganizationProfile entity (for logo_url), active-caregiver count.
        `categories` is the already-resolved, once-per-search() list (see
        search()) — service names are derived from it in Python, never a
        per-card query. Only ever called with the already-paginated
        PAGE_SIZE-limited set actually being rendered, never the full
        candidate set — see quality/DEFECT_AND_RISK_REGISTER.md KL-012 and
        CaregiverDirectoryService._bulk_card_data()'s identical precedent."""
        supplier_ids = [supplier.id for supplier in suppliers]
        entities_by_supplier_id = resolve_supplier_entities_bulk(suppliers)
        organizations = [entity for entity in entities_by_supplier_id.values() if entity is not None]
        return {
            "ratings": common.rating_summaries_bulk(supplier_ids),
            "entities_by_supplier_id": entities_by_supplier_id,
            "active_provider_counts": OrganizationStaffService.list_active_caregiver_counts_bulk(organizations),
            "categories": categories,
        }

    @classmethod
    def _build_card(cls, supplier, attrs, *, card_data) -> OrganizationCardViewModel:
        rating = card_data["ratings"].get(supplier.id) or RatingSummaryViewModel(
            average=None, review_count=0, stars_rounded=0,
        )
        entity = card_data["entities_by_supplier_id"].get(supplier.id)
        active_provider_count = card_data["active_provider_counts"].get(entity.id, 0) if entity else 0

        return OrganizationCardViewModel(
            supplier_id=supplier.id,
            name=supplier.display_name,
            logo_initial=common.avatar_initial(supplier.display_name),
            logo_url=entity.logo.url if entity and entity.logo else "",
            headline=attrs["headline"],
            city=attrs["city"],
            service_names=cls._service_names(supplier, categories=card_data["categories"]),
            verification_status=attrs["verification_status"],
            verification_label=common.verification_label(attrs["verification_status"]),
            is_verified=attrs["verification_status"] == "verified",
            rating=rating,
            active_provider_count=active_provider_count,
            profile_url=f"/find-an-organization/{supplier.id}/",
        )

    @staticmethod
    def _service_names(supplier, *, categories) -> tuple[str, ...]:
        """Derives the supplier's service names from an already-resolved
        `categories` list (see search()'s single, once-per-call fetch) —
        never issues a query itself, unlike
        OrganizationPublicProfileService._service_names()'s own single-
        supplier equivalent (fine there — one query for exactly one
        profile page — but would have been a per-card N+1 here)."""
        category_ids = {str(cid) for cid in (supplier.service_categories or [])}
        if not category_ids:
            return ()
        return tuple(category.name for category in categories if str(category.id) in category_ids)

    @classmethod
    def _build_filters(cls, *, tenant_id, text, city, service_category_id, categories):
        cities = cls.available_cities(tenant_id=tenant_id)
        normalized_city = " ".join((city or "").split()).casefold() or None

        city_options = tuple(
            FilterOptionViewModel(value=c, label=c, selected=(normalized_city == c.casefold())) for c in cities
        )
        service_options = tuple(
            FilterOptionViewModel(value=str(cat.id), label=cat.name, selected=(str(cat.id) == str(service_category_id)))
            for cat in categories
        )

        return OrganizationDirectoryFiltersViewModel(
            city_options=city_options,
            service_options=service_options,
            search_text=text or "",
        )
