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
            candidates = [supplier for supplier in candidates if cls._matches_city(supplier, query.city)]

        if query.requested_start is not None and query.requested_end is not None:
            candidates = [
                supplier for supplier in candidates
                if cls._is_available_for_range(supplier, query.requested_start, query.requested_end)
            ]

        return candidates

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _matches_city(supplier: ServiceSupplier, city: str) -> bool:
        from apps.accounts.services.supplier_bridge import resolve_supplier_entity

        entity = resolve_supplier_entity(supplier)
        entity_city = getattr(entity, "city", "") or ""
        return entity_city.strip().casefold() == city

    @staticmethod
    def _is_available_for_range(supplier: ServiceSupplier, start, end) -> bool:
        from apps.availability.services import AvailabilityError, AvailabilityQueryService

        try:
            return AvailabilityQueryService.is_supplier_available(supplier=supplier, start=start, end=end)
        except AvailabilityError:
            return False
