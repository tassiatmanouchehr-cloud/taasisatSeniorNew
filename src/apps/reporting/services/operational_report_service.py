"""
OperationalReportService — Module 16 foundation.

Read-only order-lifecycle aggregation. Never mutates Order or any other
operational model.
"""

import uuid

from django.db.models import Count

from apps.orders.models import FINAL_STATUSES, Order, OrderStatus

from ..dto import OrderCountsReport


class OperationalReportService:
    """Deterministic, tenant-scoped order-count aggregation."""

    @classmethod
    def get_order_counts(cls, tenant_id: uuid.UUID) -> OrderCountsReport:
        rows = Order.objects.for_tenant(tenant_id).values("status").annotate(count=Count("id")).order_by("status")

        by_status = {row["status"]: row["count"] for row in rows}

        completed = by_status.get(OrderStatus.COMPLETED, 0)
        cancelled = by_status.get(OrderStatus.CANCELLED, 0)
        total = sum(by_status.values())
        active = sum(count for status, count in by_status.items() if status not in FINAL_STATUSES)

        return OrderCountsReport(
            tenant_id=tenant_id,
            total_orders=total,
            active_orders=active,
            completed_orders=completed,
            cancelled_orders=cancelled,
            by_status=by_status,
        )
