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
        ).select_related("service_category").order_by("-created_at")[:limit]

    @classmethod
    def list_for_customer(cls, *, customer_profile, tenant_id, only=None):
        """`only`: None (all), "active", "completed", or "cancelled" — Customer
        Experience Phase 2 order-history tabs. select_related("elder_profile")
        avoids the N+1 templates/portal/requests_list.html's
        order.elder_profile.full_name would otherwise cause per row (Epic 07
        query-count regression test caught this)."""
        from ..models import FINAL_STATUSES, Order, OrderStatus

        queryset = Order.objects.for_tenant(tenant_id).filter(
            customer_profile=customer_profile,
        ).select_related("service_category", "elder_profile").order_by("-created_at")

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
        ).select_related("service_category").exclude(status__in=FINAL_STATUSES).order_by("scheduled_for")[:limit]

    @classmethod
    def list_for_care_recipient(cls, *, customer_profile, elder_profile, tenant_id):
        """Orders for one specific care recipient — Epic 07 (Customer
        Portal Completion). Double-scoped (customer_profile AND
        elder_profile) even though elder_profile.customer_profile is
        already guaranteed to match by CareRecipientService.get_for_customer
        — defense in depth, matching every other method's own-customer-only
        scoping in this class. select_related("service_category") avoids
        the N+1 CareRecipientPresentationService._order_row() would
        otherwise cause reading order.service_category.name per row."""
        from ..models import Order

        return Order.objects.for_tenant(tenant_id).filter(
            customer_profile=customer_profile,
            elder_profile=elder_profile,
        ).select_related("service_category").order_by("-created_at")

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
        status. Tenant-wide, not organization-scoped — retained for any
        genuinely tenant-wide/platform-admin caller (none exist today).
        apps.organization_portal must never call this directly — see
        list_eligible_for_organization(), which replaced it as the
        Assignment Center's query as of Epic 04 (Enterprise Organization
        Isolation). See GAP_ANALYSIS.md's "Organization Assignment Center
        is tenant-wide, not organization-scoped" section for the gap this
        closed."""
        from ..models import FINAL_STATUSES, Order

        return Order.objects.for_tenant(tenant_id).filter(
            assigned_supplier__isnull=True,
        ).exclude(status__in=FINAL_STATUSES).order_by("created_at")

    @classmethod
    def list_recent_unassigned_for_tenant(cls, *, tenant_id, limit):
        return cls.list_unassigned_for_tenant(tenant_id=tenant_id)[:limit]

    @classmethod
    def list_for_supplier(cls, *, supplier, tenant_id, only=None, limit=None):
        """`only`: None (all), "current" (IN_PROGRESS), "upcoming"
        (WAITING_SERVICE), "completed", or "cancelled" — Sprint 2.5
        (Caregiver Professional Dashboard) work-summary tabs. Mirrors
        list_for_customer()'s exact shape, scoped by assigned_supplier
        instead of customer_profile. No new statuses invented — these are
        Order.status's own existing values (see orders.models.OrderStatus)."""
        from ..models import Order, OrderStatus

        queryset = Order.objects.for_tenant(tenant_id).filter(
            assigned_supplier=supplier,
        ).select_related("service_category").order_by("-created_at")

        if only == "current":
            queryset = queryset.filter(status=OrderStatus.IN_PROGRESS)
        elif only == "upcoming":
            queryset = queryset.filter(status=OrderStatus.WAITING_SERVICE)
        elif only == "completed":
            queryset = queryset.filter(status=OrderStatus.COMPLETED)
        elif only == "cancelled":
            queryset = queryset.filter(status=OrderStatus.CANCELLED)

        return queryset[:limit] if limit else queryset

    @classmethod
    def count_by_status_for_supplier(cls, *, supplier, tenant_id) -> dict:
        """Single aggregate query — the dashboard summary counts, without
        loading full row sets for a caregiver with a long order history."""
        from django.db.models import Count, Q

        from ..models import Order, OrderStatus

        counts = Order.objects.for_tenant(tenant_id).filter(assigned_supplier=supplier).aggregate(
            current=Count("id", filter=Q(status=OrderStatus.IN_PROGRESS)),
            upcoming=Count("id", filter=Q(status=OrderStatus.WAITING_SERVICE)),
            completed=Count("id", filter=Q(status=OrderStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=OrderStatus.CANCELLED)),
        )
        return {key: (value or 0) for key, value in counts.items()}

    @classmethod
    def count_unassigned_for_tenant(cls, *, tenant_id):
        return cls.list_unassigned_for_tenant(tenant_id=tenant_id).count()

    @classmethod
    def list_eligible_for_organization(cls, *, organization, tenant_id):
        """Epic 04 (Enterprise Organization Isolation): the organization
        portal's Assignment Center query — replaces
        list_unassigned_for_tenant() as that view's source. Returns
        unassigned, non-final orders with an ACTIVE
        OrderOrganizationEligibility row for `organization`: the claimable
        work list, organization-scoped instead of tenant-wide.

        Deliberately excludes already-assigned orders, matching the
        pre-Epic-04 "open orders" semantics exactly (an assigned order is
        no longer open work) — the organization does not lose the ability
        to *act on* an order it already owns once assigned (see
        apps.booking.services.organization_assignment
        .OrganizationAssignmentService._already_assigned_to_organization,
        the reassignment-permission guarantee), it simply drops off this
        specific "still claimable" list, exactly as before."""
        from ..models import FINAL_STATUSES, EligibilityStatus, Order

        return Order.objects.for_tenant(tenant_id).filter(
            assigned_supplier__isnull=True,
            organization_eligibilities__organization=organization,
            organization_eligibilities__status=EligibilityStatus.ACTIVE,
        ).exclude(status__in=FINAL_STATUSES).order_by("created_at")

    @classmethod
    def list_recent_eligible_for_organization(cls, *, organization, tenant_id, limit):
        return cls.list_eligible_for_organization(organization=organization, tenant_id=tenant_id)[:limit]

    @classmethod
    def count_eligible_for_organization(cls, *, organization, tenant_id):
        return cls.list_eligible_for_organization(organization=organization, tenant_id=tenant_id).count()


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
