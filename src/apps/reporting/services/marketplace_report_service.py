"""
MarketplaceReportService — Module 16 foundation.

Read-only marketplace-composition aggregation (suppliers, organizations,
customers, category distribution). Never mutates any of them. Never
aggregates across tenants.
"""

import uuid

from django.db.models import Count

from apps.accounts.models.profiles import CustomerProfile, OrganizationProfile
from apps.kernel.models.supplier import ServiceSupplier
from apps.orders.models import Order

from ..dto import MarketplaceStatsReport
from .configuration import ReportingConfiguration


class MarketplaceReportService:
    """Deterministic, tenant-scoped marketplace composition aggregation."""

    @classmethod
    def get_marketplace_stats(cls, tenant_id: uuid.UUID) -> MarketplaceStatsReport:
        supplier_rows = (
            ServiceSupplier.objects.filter(tenant_id=tenant_id)
            .values("supplier_type")
            .annotate(count=Count("id"))
            .order_by("supplier_type")
        )
        supplier_type_distribution = {row["supplier_type"]: row["count"] for row in supplier_rows}
        supplier_count = sum(supplier_type_distribution.values())

        organization_count = OrganizationProfile.objects.filter(tenant_id=tenant_id).count()
        customer_count = CustomerProfile.objects.filter(person__tenant_id=tenant_id).count()

        limit = ReportingConfiguration.get_category_distribution_limit(tenant_id=tenant_id)
        category_rows = (
            Order.objects.for_tenant(tenant_id)
            .values("service_category__name")
            .annotate(count=Count("id"))
            .order_by("-count", "service_category__name")[:limit]
        )
        category_distribution = {
            (row["service_category__name"] or "Unknown"): row["count"] for row in category_rows
        }

        return MarketplaceStatsReport(
            tenant_id=tenant_id,
            supplier_count=supplier_count,
            organization_count=organization_count,
            customer_count=customer_count,
            supplier_type_distribution=supplier_type_distribution,
            category_distribution=category_distribution,
        )
