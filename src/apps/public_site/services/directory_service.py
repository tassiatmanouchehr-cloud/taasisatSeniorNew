"""
CaregiverDirectoryService — Epic 06 (Marketplace Profiles & Discovery).

Builds the public Caregiver Directory page. Reuses apps.discovery's
existing search/ranking building blocks directly (SupplierSearchService
.filter_suppliers() + DiscoveryRankingService.rank()) rather than
apps.discovery.services.discovery_service.DiscoveryService.search()
itself, because that orchestration accepts exactly one supplier_type
value. This directory must show both INDEPENDENT_PROVIDER and
ORGANIZATION_PROVIDER suppliers together (real caregivers) while never
showing a plain ORGANIZATION supplier (a company has no bio/specialty/
years_experience — it isn't a caregiver profile) — so the two allowed
types are queried and ranked together here instead. Nothing in
apps.discovery is modified.

Architecture Review remediation (M1, PR #36): _filter_candidates() now
returns both the eligible suppliers AND their already-resolved attrs
dict (from common.bulk_supplier_attrs() — one batched CaregiverProfile
query and one batched OrganizationMembership query, regardless of
candidate count). Every caller (search(), featured(), available_cities())
reuses that same attrs dict for eligibility filtering, city dedup, and
card building — nothing here re-fetches a CaregiverProfile row that was
already resolved earlier in the same call.
"""

import math

from apps.discovery.services.query_normalizer import normalize_query
from apps.discovery.services.ranking_service import DiscoveryRankingService
from apps.discovery.services.search_service import SupplierSearchService
from apps.kernel.models.supplier import AvailabilityStatus, ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.services.tenant_service import TenantService
from apps.orders.services.queries import CatalogQueryService

from . import common
from .viewmodels import (
    CaregiverCardViewModel,
    DirectoryFiltersViewModel,
    DirectoryPageViewModel,
    FilterOptionViewModel,
    RatingSummaryViewModel,
)

CAREGIVER_SUPPLIER_TYPES = (SupplierType.INDEPENDENT_PROVIDER, SupplierType.ORGANIZATION_PROVIDER)

PAGE_SIZE = 12

TYPE_LABELS = {
    SupplierType.INDEPENDENT_PROVIDER: "مستقل",
    SupplierType.ORGANIZATION_PROVIDER: "وابسته به سازمان",
}


class CaregiverDirectoryService:
    """Read-only: search + filter + paginate the public caregiver directory."""

    @classmethod
    def search(
        cls,
        *,
        tenant_id=None,
        tenant_slug=None,
        text="",
        city=None,
        supplier_type=None,
        service_category_id=None,
        availability_status=None,
        page=1,
        base_url="/find-a-caregiver/",
    ) -> DirectoryPageViewModel:
        tenant_id = tenant_id or TenantService.get_default_tenant_id()

        allowed_types = (supplier_type,) if supplier_type in CAREGIVER_SUPPLIER_TYPES else CAREGIVER_SUPPLIER_TYPES
        candidates, attrs_by_id = cls._filter_candidates(
            tenant_id=tenant_id,
            allowed_types=allowed_types,
            text=text,
            city=city,
            service_category_id=service_category_id,
            availability_status=availability_status,
        )
        candidates_by_id = {supplier.id: supplier for supplier in candidates}
        ranked = DiscoveryRankingService.rank(tenant_id=tenant_id, suppliers=candidates)

        total_count = len(ranked)
        total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
        current_page = max(1, min(common.parse_page(page), total_pages))
        offset = (current_page - 1) * PAGE_SIZE
        page_items = ranked[offset : offset + PAGE_SIZE]
        page_supplier_ids = [item.supplier_id for item in page_items if item.supplier_id in candidates_by_id]

        card_data = cls._bulk_card_data(tenant_id=tenant_id, supplier_ids=page_supplier_ids)
        cards = tuple(
            cls._build_card(
                candidates_by_id[supplier_id], attrs_by_id[supplier_id], card_data=card_data, tenant_slug=tenant_slug,
            )
            for supplier_id in page_supplier_ids
        )

        filters = cls._build_filters(
            tenant_id=tenant_id,
            text=text,
            city=city,
            supplier_type=supplier_type,
            service_category_id=service_category_id,
            availability_status=availability_status,
            tenant_slug=tenant_slug,
            base_url=base_url,
        )
        pagination = cls._build_pagination(
            current_page=current_page,
            total_pages=total_pages,
            total_count=total_count,
            base_url=base_url,
            text=text,
            city=city,
            supplier_type=supplier_type,
            service_category_id=service_category_id,
            availability_status=availability_status,
            tenant_slug=tenant_slug,
        )

        return DirectoryPageViewModel(caregivers=cards, filters=filters, pagination=pagination)

    @classmethod
    def available_cities(cls, *, tenant_id=None) -> tuple[str, ...]:
        """Distinct cities among all currently active, publicly-visible
        caregivers — used to populate the city selector on both this
        directory and the Home Page, unaffected by any active filter."""
        tenant_id = tenant_id or TenantService.get_default_tenant_id()
        _candidates, attrs_by_id = cls._filter_candidates(
            tenant_id=tenant_id,
            allowed_types=CAREGIVER_SUPPLIER_TYPES,
            text="",
            city=None,
            service_category_id=None,
            availability_status=None,
        )
        return common.distinct_cities_from_attrs(attrs_by_id.values())

    @classmethod
    def featured(cls, *, tenant_id=None, tenant_slug=None, limit=4) -> tuple[CaregiverCardViewModel, ...]:
        """Top-ranked caregivers for the Home Page's "Featured Caregivers"
        section — same ranking as the directory itself, no filters.

        tenant_slug (follow-up to FR-016): threaded into each card's
        profile_url exactly like search()'s own tenant_slug, so a
        featured-caregiver card on a tenant-hinted/tenant-configured
        homepage still resolves when clicked. Defaults to None — every
        pre-existing caller (Home Page with no active hint) is
        byte-identical to before."""
        tenant_id = tenant_id or TenantService.get_default_tenant_id()

        candidates, attrs_by_id = cls._filter_candidates(
            tenant_id=tenant_id,
            allowed_types=CAREGIVER_SUPPLIER_TYPES,
            text="",
            city=None,
            service_category_id=None,
            availability_status=None,
        )
        candidates_by_id = {supplier.id: supplier for supplier in candidates}
        ranked = DiscoveryRankingService.rank(tenant_id=tenant_id, suppliers=candidates)

        featured_supplier_ids = [item.supplier_id for item in ranked[:limit] if item.supplier_id in candidates_by_id]
        card_data = cls._bulk_card_data(tenant_id=tenant_id, supplier_ids=featured_supplier_ids)
        return tuple(
            cls._build_card(
                candidates_by_id[supplier_id], attrs_by_id[supplier_id], card_data=card_data, tenant_slug=tenant_slug,
            )
            for supplier_id in featured_supplier_ids
        )

    @classmethod
    def build_cards_for_supplier_ids(cls, supplier_ids, *, tenant_id=None) -> dict:
        """Phase 4 Sprint 4.1 (Customer Favorites): resolves an explicit,
        caller-chosen set of supplier ids into cards, for surfaces that
        already know exactly which suppliers they want (a customer's
        favorites list) rather than running search()'s own ranking/
        pagination over the full candidate universe. Reuses the exact same
        KL-012-hardened `_bulk_card_data()`/`_build_card()` machinery
        search()/featured() already use — no second card-building
        implementation. Returns {supplier_id: CaregiverCardViewModel},
        silently omitting any id that is not currently publicly visible
        (the caller distinguishes "not in this dict" from "favorited but no
        longer public")."""
        tenant_id = tenant_id or TenantService.get_default_tenant_id()
        if not supplier_ids:
            return {}

        suppliers = list(
            ServiceSupplier.objects.filter(
                id__in=supplier_ids, tenant_id=tenant_id, status=SupplierStatus.ACTIVE,
                supplier_type__in=CAREGIVER_SUPPLIER_TYPES,
            ),
        )
        attrs_by_id = common.bulk_supplier_attrs(suppliers)
        eligible = [supplier for supplier in suppliers if common.is_publicly_visible_attrs(attrs_by_id[supplier.id])]

        card_data = cls._bulk_card_data(tenant_id=tenant_id, supplier_ids=[supplier.id for supplier in eligible])
        return {
            supplier.id: cls._build_card(supplier, attrs_by_id[supplier.id], card_data=card_data)
            for supplier in eligible
        }

    # ------------------------------------------------------------------

    @classmethod
    def _filter_candidates(cls, *, tenant_id, allowed_types, text, city, service_category_id, availability_status):
        """Returns (eligible_suppliers, attrs_by_id) — attrs_by_id covers
        every eligible supplier and is computed via exactly one batched
        resolution pass (common.bulk_supplier_attrs()), reused by every
        caller instead of being recomputed per supplier."""
        candidates = []
        for a_type in allowed_types:
            query = normalize_query(
                tenant_id=tenant_id,
                text=text,
                service_category_id=service_category_id,
                supplier_type=a_type,
                availability_status=availability_status,
                city=city,
            )
            candidates.extend(SupplierSearchService.filter_suppliers(query))

        attrs_by_id = common.bulk_supplier_attrs(candidates)
        eligible = [supplier for supplier in candidates if common.is_publicly_visible_attrs(attrs_by_id[supplier.id])]
        return eligible, {supplier.id: attrs_by_id[supplier.id] for supplier in eligible}

    @staticmethod
    def _bulk_card_data(*, tenant_id, supplier_ids) -> dict:
        """Precomputes, in a small fixed number of queries regardless of
        how many supplier_ids are passed, the two per-card values that
        used to be resolved with one query call *per card* inside
        _build_card() — rating (common.rating_summary()) and completed-
        jobs count (common.completed_jobs_count()). Only ever called with
        the already-paginated/limited set of supplier_ids actually being
        rendered (PAGE_SIZE or `limit`), never the full candidate set —
        see quality/DEFECT_AND_RISK_REGISTER.md KL-012."""
        return {
            "ratings": common.rating_summaries_bulk(supplier_ids),
            "completed_jobs": common.completed_jobs_counts_bulk(tenant_id=tenant_id, supplier_ids=supplier_ids),
        }

    @classmethod
    def _build_card(cls, supplier, attrs, *, card_data, tenant_slug=None) -> CaregiverCardViewModel:
        rating = card_data["ratings"].get(supplier.id) or RatingSummaryViewModel(
            average=None, review_count=0, stars_rounded=0,
        )
        return CaregiverCardViewModel(
            supplier_id=supplier.id,
            display_name=supplier.display_name,
            avatar_initial=common.avatar_initial(supplier.display_name),
            city=attrs["city"],
            specialty=attrs["specialty"],
            bio_snippet=common.bio_snippet(attrs["bio"]),
            is_organization_affiliated=common.is_organization_affiliated(supplier),
            availability_status=supplier.availability_status,
            availability_label=common.availability_label(supplier.availability_status),
            avatar_status_dot=common.avatar_status_dot(supplier.availability_status),
            verification_status=attrs["verification_status"],
            verification_label=common.verification_label(attrs["verification_status"]),
            is_verified=attrs["verification_status"] == "verified",
            rating=rating,
            completed_jobs=card_data["completed_jobs"].get(supplier.id, 0),
            profile_url=common.append_tenant_query(f"/find-a-caregiver/{supplier.id}/", tenant_slug),
        )

    @classmethod
    def _build_filters(
        cls, *, tenant_id, text, city, supplier_type, service_category_id, availability_status,
        tenant_slug=None, base_url="/find-a-caregiver/",
    ):
        cities = cls.available_cities(tenant_id=tenant_id)
        normalized_city = " ".join((city or "").split()).casefold() or None

        city_options = tuple(
            FilterOptionViewModel(value=c, label=c, selected=(normalized_city == c.casefold())) for c in cities
        )
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).order_by("sort_order", "name")
        service_options = tuple(
            FilterOptionViewModel(value=str(cat.id), label=cat.name, selected=(str(cat.id) == str(service_category_id)))
            for cat in categories
        )
        type_options = tuple(
            FilterOptionViewModel(value=t, label=TYPE_LABELS[t], selected=(supplier_type == t))
            for t in CAREGIVER_SUPPLIER_TYPES
        )
        availability_options = tuple(
            FilterOptionViewModel(
                value=status,
                label=common.availability_label(status),
                selected=(availability_status == status),
            )
            for status in AvailabilityStatus.values
        )

        return DirectoryFiltersViewModel(
            city_options=city_options,
            service_options=service_options,
            type_options=type_options,
            availability_options=availability_options,
            search_text=text or "",
            gender_filter_supported=False,
            tenant_slug=tenant_slug or "",
            reset_url=common.append_tenant_query(base_url, tenant_slug),
        )

    @classmethod
    def _build_pagination(
        cls,
        *,
        current_page,
        total_pages,
        total_count,
        base_url,
        text,
        city,
        supplier_type,
        service_category_id,
        availability_status,
        tenant_slug=None,
    ):
        params = {}
        if text:
            params["q"] = text
        if city:
            params["city"] = city
        if supplier_type:
            params["type"] = supplier_type
        if service_category_id:
            params["service"] = str(service_category_id)
        if availability_status:
            params["availability"] = availability_status
        if tenant_slug:
            params["tenant"] = tenant_slug

        return common.build_pagination(
            current_page=current_page,
            total_pages=total_pages,
            total_count=total_count,
            base_url=base_url,
            params=params,
        )
