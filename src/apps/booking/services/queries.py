"""
ProviderAssignmentQueryService — Epic 02 (Marketplace Operational
Experience). Read-only SupplierAssignment lookups scoped to a specific
supplier, so apps.provider_portal (and any future consumer) never touches
the ORM directly (ADR-007's thin-controller rule) and never has to
re-derive "which assignment attempt is the current one for this order and
this supplier."
"""


class ProviderAssignmentNotFoundError(Exception):
    """Raised when an order has no assignment attempt for the given supplier."""


class ProviderAssignmentQueryService:
    """Read-only SupplierAssignment lookups, always scoped to a tenant and a supplier."""

    @classmethod
    def list_for_supplier(cls, *, supplier, tenant_id, only=None):
        """`only`: None (all), "pending" (awaiting provider confirm/decline), or
        "confirmed"."""
        from ..models import SupplierAssignment, SupplierAssignmentStatus

        queryset = SupplierAssignment.objects.for_tenant(tenant_id).filter(
            supplier=supplier,
        ).select_related("order").order_by("-created_at")

        if only == "pending":
            queryset = queryset.filter(
                status__in=[SupplierAssignmentStatus.PROPOSED, SupplierAssignmentStatus.ASSIGNED],
            )
        elif only == "confirmed":
            queryset = queryset.filter(status=SupplierAssignmentStatus.CONFIRMED)

        return queryset

    @classmethod
    def get_for_supplier(cls, *, supplier, tenant_id, order_id):
        """The most recent assignment attempt for this supplier on this order —
        the "current" one from this supplier's point of view. Raises
        ProviderAssignmentNotFoundError if this supplier was never assigned to
        this order (never leaks whether the order itself exists)."""
        from ..models import SupplierAssignment

        assignment = SupplierAssignment.objects.for_tenant(tenant_id).filter(
            order_id=order_id, supplier=supplier,
        ).select_related("order").order_by("-assignment_sequence").first()

        if assignment is None:
            raise ProviderAssignmentNotFoundError("Assignment not found.")
        return assignment
