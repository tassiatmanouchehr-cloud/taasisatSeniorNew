"""
Read-only query services — Customer Experience Phase 1 remediation.

Centralizes the Order/ServiceCategory/ServiceType reads apps.portal (and
any future consumer, e.g. a customer API) needs, so views never call the
ORM directly (ADR-007's thin-controller rule). Ownership/tenant scoping
lives here, once, rather than being re-derived at each call site.
"""


class OrderNotFoundError(Exception):
    """Raised when a tenant/ownership-scoped Order lookup fails. Deliberately
    does not distinguish "doesn't exist" from "exists but isn't yours" —
    callers should map this to a 404, not leak cross-customer existence."""


class OrderQueryService:
    """Read-only Order lookups, always scoped to a tenant and (where given) a customer."""

    @classmethod
    def list_recent_for_customer(cls, *, customer_profile, tenant_id, limit):
        from ..models import Order

        return Order.objects.for_tenant(tenant_id).filter(
            customer_profile=customer_profile,
        ).order_by("-created_at")[:limit]

    @classmethod
    def list_for_customer(cls, *, customer_profile, tenant_id, only=None):
        """`only`: None (all), "active", "completed", or "cancelled" — Customer
        Experience Phase 2 order-history tabs."""
        from ..models import FINAL_STATUSES, Order, OrderStatus

        queryset = Order.objects.for_tenant(tenant_id).filter(
            customer_profile=customer_profile,
        ).order_by("-created_at")

        if only == "active":
            queryset = queryset.exclude(status__in=FINAL_STATUSES)
        elif only == "completed":
            queryset = queryset.filter(status=OrderStatus.COMPLETED)
        elif only == "cancelled":
            queryset = queryset.filter(status=OrderStatus.CANCELLED)

        return queryset

    @classmethod
    def list_upcoming_for_customer(cls, *, customer_profile, tenant_id, limit):
        """Orders with a future scheduled_for and a non-final status — the
        dashboard's "upcoming visits" slice (Customer Experience Phase 2)."""
        from django.utils import timezone

        from ..models import FINAL_STATUSES, Order

        return Order.objects.for_tenant(tenant_id).filter(
            customer_profile=customer_profile,
            scheduled_for__gte=timezone.now(),
        ).exclude(status__in=FINAL_STATUSES).order_by("scheduled_for")[:limit]

    @classmethod
    def get_for_customer(cls, *, customer_profile, tenant_id, order_id):
        from ..models import Order

        try:
            return Order.objects.for_tenant(tenant_id).get(id=order_id, customer_profile=customer_profile)
        except Order.DoesNotExist:
            raise OrderNotFoundError("Order not found.")

    @classmethod
    def list_unassigned_for_tenant(cls, *, tenant_id):
        """Orders in this tenant with no supplier assigned yet and a non-final
        status — the organization portal's Assignment Center (Epic 02).
        Deliberately tenant-wide, not filtered by service category/
        eligibility — every organization admin in the tenant sees the same
        open-work list today. NOT organization-scoped and not yet safe for
        a tenant hosting more than one organization with unrelated or
        competing interests — see GAP_ANALYSIS.md's "Organization
        Assignment Center is tenant-wide, not organization-scoped" section
        for the full risk writeup and what's required to close it."""
        from ..models import FINAL_STATUSES, Order

        return Order.objects.for_tenant(tenant_id).filter(
            assigned_supplier__isnull=True,
        ).exclude(status__in=FINAL_STATUSES).order_by("created_at")

    @classmethod
    def list_recent_unassigned_for_tenant(cls, *, tenant_id, limit):
        return cls.list_unassigned_for_tenant(tenant_id=tenant_id)[:limit]

    @classmethod
    def count_unassigned_for_tenant(cls, *, tenant_id):
        return cls.list_unassigned_for_tenant(tenant_id=tenant_id).count()


class CatalogNotFoundError(Exception):
    """Raised when a tenant-scoped ServiceCategory/ServiceType lookup fails."""


class CatalogQueryService:
    """Read-only ServiceCategory/ServiceType lookups, always tenant-scoped."""

    @classmethod
    def list_active_categories(cls, *, tenant_id):
        from ..models import CatalogStatus, ServiceCategory

        return ServiceCategory.objects.for_tenant(tenant_id).filter(status=CatalogStatus.ACTIVE)

    @classmethod
    def get_active_category(cls, *, tenant_id, category_id):
        """Raises CatalogNotFoundError for a missing, cross-tenant, or inactive category."""
        from ..models import CatalogStatus, ServiceCategory

        try:
            return ServiceCategory.objects.for_tenant(tenant_id).get(id=category_id, status=CatalogStatus.ACTIVE)
        except ServiceCategory.DoesNotExist:
            raise CatalogNotFoundError("Service category not found.")

    @classmethod
    def get_category(cls, *, tenant_id, category_id):
        """Tenant-scoped lookup without an active-status filter — for display
        steps (e.g. wizard review) where the category was already validated
        as active earlier in the same flow."""
        from ..models import ServiceCategory

        try:
            return ServiceCategory.objects.for_tenant(tenant_id).get(id=category_id)
        except ServiceCategory.DoesNotExist:
            raise CatalogNotFoundError("Service category not found.")

    @classmethod
    def list_active_types_grouped_by_category(cls, *, tenant_id, categories):
        """Returns {category_id: [{"id": ..., "name": ...}, ...]} — JSON-serializable
        shape for the wizard's client-side category-to-type filter."""
        from ..models import CatalogStatus, ServiceType

        return {
            str(category.id): [
                {"id": str(service_type.id), "name": service_type.name}
                for service_type in ServiceType.objects.for_tenant(tenant_id).filter(
                    category=category, status=CatalogStatus.ACTIVE,
                )
            ]
            for category in categories
        }

    @classmethod
    def get_type_or_none(cls, *, tenant_id, type_id):
        from ..models import ServiceType

        return ServiceType.objects.for_tenant(tenant_id).filter(id=type_id).first()
