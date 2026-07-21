"""
ProviderExecutionQueryService — Epic 02 (Marketplace Operational
Experience). Read-only ExecutionSession lookups scoped to a specific
supplier, so apps.provider_portal never touches the ORM directly.
"""


class ProviderExecutionQueryService:
    """Read-only ExecutionSession lookups, always scoped to a tenant and a supplier."""

    @classmethod
    def list_active_for_supplier(cls, *, supplier, tenant_id):
        from ..models import ExecutionSession, ExecutionSessionStatus

        return (
            ExecutionSession.objects.for_tenant(tenant_id)
            .filter(
                supplier_assignment__supplier=supplier,
                status=ExecutionSessionStatus.IN_PROGRESS,
            )
            .select_related("order")
            .order_by("-started_at")
        )

    @classmethod
    def list_completed_for_supplier(cls, *, supplier, tenant_id, limit=None):
        from ..models import ExecutionSession, ExecutionSessionStatus

        queryset = (
            ExecutionSession.objects.for_tenant(tenant_id)
            .filter(
                supplier_assignment__supplier=supplier,
                status__in=[ExecutionSessionStatus.PROVIDER_COMPLETED, ExecutionSessionStatus.CLOSED],
            )
            .select_related("order")
            .order_by("-provider_completed_at")
        )

        return queryset[:limit] if limit else queryset

    @classmethod
    def get_for_order_and_supplier(cls, *, order_id, supplier, tenant_id):
        """The most recent execution session for this supplier on this order, or
        None — not every confirmed assignment has a session yet."""
        from ..models import ExecutionSession

        return (
            ExecutionSession.objects.for_tenant(tenant_id)
            .filter(
                order_id=order_id,
                supplier_assignment__supplier=supplier,
            )
            .order_by("-execution_sequence")
            .first()
        )
