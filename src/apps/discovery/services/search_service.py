"""
SupplierSearchService — Module 12 foundation.

Filters ServiceSupplier candidates for a normalized SearchQuery. City
filtering goes through the sanctioned apps.accounts.services.supplier_bridge
.resolve_supplier_entity() translator (read-only) — never CaregiverProfile/
OrganizationProfile directly. Availability filtering only runs when both
requested_start and requested_end are present on the query.
"""

from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus

from .dto import SearchQuery
from .errors import DiscoveryError


class SupplierSearchService:
    """Tenant-scoped, active-only supplier filtering."""

    @classmethod
    def filter_suppliers(cls, query: SearchQuery) -> list[ServiceSupplier]:
        if (query.requested_start is None) != (query.requested_end is None):
            raise DiscoveryError("requested_start and requested_end must both be supplied, or neither.")

        qs = ServiceSupplier.objects.filter(tenant_id=query.tenant_id, status=SupplierStatus.ACTIVE)

        if query.text:
            qs = qs.filter(display_name__icontains=query.text)
        if query.service_category_id:
            qs = qs.filter(service_categories__contains=[str(query.service_category_id)])
        if query.supplier_type:
            qs = qs.filter(supplier_type=query.supplier_type)
        if query.availability_status:
            qs = qs.filter(availability_status=query.availability_status)
        if query.verification_level:
            qs = qs.filter(verification_level=query.verification_level)

        candidates = list(qs.order_by("id"))

        if query.city:
            candidates = cls._filter_by_city(candidates, query.city)

        if query.requested_start is not None and query.requested_end is not None:
            candidates = [
                supplier
                for supplier in candidates
                if cls._is_available_for_range(supplier, query.requested_start, query.requested_end)
            ]

        return candidates

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _filter_by_city(candidates: list[ServiceSupplier], city: str) -> list[ServiceSupplier]:
        """Batched city filter — resolves every candidate's accounts-side
        entity in at most two queries total (resolve_supplier_entities_bulk(),
        the same bulk resolver apps.public_site.services.common
        .bulk_supplier_attrs() already uses), instead of one
        resolve_supplier_entity() query per candidate. Previously this was
        a per-candidate lookup inside a Python list comprehension — a
        genuine N+1 (quality/DEFECT_AND_RISK_REGISTER.md KL-012's second
        source, alongside DiscoveryRankingService's per-candidate capacity
        check)."""
        from apps.accounts.services.supplier_bridge import resolve_supplier_entities_bulk

        normalized_city = city.strip().casefold()
        entities_by_supplier_id = resolve_supplier_entities_bulk(candidates)
        return [
            supplier
            for supplier in candidates
            if (getattr(entities_by_supplier_id.get(supplier.id), "city", "") or "").strip().casefold()
            == normalized_city
        ]

    @staticmethod
    def _is_available_for_range(supplier: ServiceSupplier, start, end) -> bool:
        from apps.availability.services import AvailabilityError, AvailabilityQueryService

        try:
            return AvailabilityQueryService.is_supplier_available(supplier=supplier, start=start, end=end)
        except AvailabilityError:
            return False
