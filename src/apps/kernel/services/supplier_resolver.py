"""
Supplier Resolver service.

Resolves ServiceSupplier entities based on the tenant's marketplace model
configuration. Business modules call this instead of directly querying
organizations or providers.

The resolver respects the marketplace.supplier_model CCS config:
- independent_only: Only INDEPENDENT_PROVIDER suppliers returned
- organization_only: Only ORGANIZATION (+ ORGANIZATION_PROVIDER) returned
- hybrid: All supplier types returned

Usage:
    from apps.kernel.services import SupplierResolver

    # Get all active suppliers for a tenant (respects marketplace model)
    suppliers = SupplierResolver.get_active_suppliers(tenant_id=tenant.id)

    # Check if a supplier type is allowed
    allowed = SupplierResolver.is_supplier_type_allowed(
        tenant_id=tenant.id,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
    )

    # Resolve a specific supplier by ID
    supplier = SupplierResolver.resolve(supplier_id, tenant_id=tenant.id)

References:
- ADR-001.03 (ServiceSupplier abstraction mandatory)
- ADR-001.04 (Three marketplace models by config)
- Architecture Intake Report Section 16.5 (Supplier Resolution Pattern)
- Phase 0.5 Deliverable 10 (Marketplace Visibility Rules)
"""

import logging
import uuid

from django.db.models import QuerySet

from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.services.config_resolver import ConfigResolver

logger = logging.getLogger(__name__)

# Marketplace model config key
MARKETPLACE_MODEL_KEY = "marketplace.supplier_model"
ALLOW_INDEPENDENT_KEY = "marketplace.allow_independent_providers"
ALLOW_ORGANIZATIONS_KEY = "marketplace.allow_organizations"
ALLOW_DIRECT_ORG_PROVIDER_KEY = "marketplace.allow_direct_organization_provider_matching"


class SupplierResolver:
    """
    Central service for resolving supplier entities.

    Business modules use this service instead of directly querying
    ServiceSupplier or any underlying identity entities. This ensures
    marketplace model configuration is always respected.

    Per ADR-001.03: No module may bypass this abstraction.
    """

    @classmethod
    def resolve(
        cls,
        supplier_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
    ) -> ServiceSupplier:
        """
        Resolve a specific supplier by ID within a tenant.

        Raises:
            ServiceSupplier.DoesNotExist: If supplier not found or wrong tenant.
        """
        return ServiceSupplier.objects.get(id=supplier_id, tenant_id=tenant_id)

    @classmethod
    def get_active_suppliers(
        cls,
        *,
        tenant_id: uuid.UUID,
        supplier_type: str | None = None,
    ) -> QuerySet:
        """
        Get active suppliers filtered by the tenant's marketplace model config.

        If supplier_type is explicitly provided, filters to that type only
        (still respects marketplace model — returns empty if type is disabled).

        Args:
            tenant_id: Tenant context.
            supplier_type: Optional explicit type filter.

        Returns:
            QuerySet of active ServiceSupplier records.
        """
        qs = ServiceSupplier.objects.filter(
            tenant_id=tenant_id,
            status=SupplierStatus.ACTIVE,
        )

        if supplier_type:
            # Explicit type requested — verify it's allowed
            if not cls.is_supplier_type_allowed(tenant_id=tenant_id, supplier_type=supplier_type):
                return qs.none()
            return qs.filter(supplier_type=supplier_type)

        # Apply marketplace model filtering
        marketplace_model = cls._get_marketplace_model(tenant_id)

        if marketplace_model == "independent_only":
            qs = qs.filter(supplier_type=SupplierType.INDEPENDENT_PROVIDER)
        elif marketplace_model == "organization_only":
            qs = qs.filter(
                supplier_type__in=[
                    SupplierType.ORGANIZATION,
                    SupplierType.ORGANIZATION_PROVIDER,
                ]
            )
        # "hybrid" — no type filter, return all active

        return qs

    @classmethod
    def is_supplier_type_allowed(
        cls,
        *,
        tenant_id: uuid.UUID,
        supplier_type: str,
    ) -> bool:
        """
        Check if a supplier type is allowed by the tenant's marketplace config.

        This is the authoritative check used by matching, assignment, and
        other modules before processing a supplier.
        """
        marketplace_model = cls._get_marketplace_model(tenant_id)

        if marketplace_model == "independent_only":
            return supplier_type == SupplierType.INDEPENDENT_PROVIDER

        elif marketplace_model == "organization_only":
            return supplier_type in (
                SupplierType.ORGANIZATION,
                SupplierType.ORGANIZATION_PROVIDER,
            )

        # hybrid — all types allowed, but check granular config
        if supplier_type == SupplierType.INDEPENDENT_PROVIDER:
            return cls._get_bool_config(ALLOW_INDEPENDENT_KEY, tenant_id, default=True)
        elif supplier_type == SupplierType.ORGANIZATION:
            return cls._get_bool_config(ALLOW_ORGANIZATIONS_KEY, tenant_id, default=True)
        elif supplier_type == SupplierType.ORGANIZATION_PROVIDER:
            return cls._get_bool_config(ALLOW_DIRECT_ORG_PROVIDER_KEY, tenant_id, default=False)

        return False

    @classmethod
    def get_suppliers_for_matching(
        cls,
        *,
        tenant_id: uuid.UUID,
        service_category_id: uuid.UUID | None = None,
        capability_ids: list[uuid.UUID] | None = None,
    ) -> QuerySet:
        """
        Get suppliers eligible for matching (active + available + type-allowed).

        Optionally filters by service category and capabilities.
        This is the entry point for Module 02 (Matching Engine).
        """
        qs = cls.get_active_suppliers(tenant_id=tenant_id)

        # Filter by availability (only available suppliers can be matched)
        qs = qs.exclude(availability_status="offline")

        # Filter by service category if specified
        if service_category_id:
            qs = qs.filter(service_categories__contains=[str(service_category_id)])

        # Capability filtering would join CapabilityAssignment (Phase 2+)
        # For now, return category-filtered results

        return qs

    @classmethod
    def _get_marketplace_model(cls, tenant_id: uuid.UUID) -> str:
        """Get the marketplace model config for a tenant."""
        try:
            value = ConfigResolver.get(MARKETPLACE_MODEL_KEY, tenant_id=tenant_id)
            if value in ("independent_only", "organization_only", "hybrid"):
                return value
        except Exception:
            pass
        # Default to hybrid if config not found or invalid
        return "hybrid"

    @classmethod
    def _get_bool_config(cls, key: str, tenant_id: uuid.UUID, default: bool = False) -> bool:
        """Get a boolean config value with safe fallback."""
        try:
            value = ConfigResolver.get(key, tenant_id=tenant_id)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
        except Exception:
            pass
        return default
