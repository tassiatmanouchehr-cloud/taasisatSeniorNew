"""
OrderTimelineService — Customer Experience Phase 1 remediation.

Read-only presentation over OrderStatusHistory + existing Order state,
mapping the OrderStatus machine onto customer-facing timeline steps. This
used to live in apps.portal.views (_timeline_for_order) — moved here
because it interprets Order/OrderStatus domain state that apps.orders
owns, not apps.portal. Any future consumer (a customer API, an admin
view) reuses this instead of re-deriving the same status interpretation.
"""

TIMELINE_STEPS = (
    ("created", "ثبت درخواست"),
    ("matching", "در حال یافتن ارائه‌دهنده"),
    ("accepted", "تخصیص ارائه‌دهنده"),
    ("scheduled", "زمان‌بندی شده"),
    ("started", "شروع خدمت"),
    ("completed", "پایان خدمت"),
)


class OrderTimelineService:
    """Builds a read-only, customer-facing timeline for a single order."""

    @classmethod
    def build(cls, order) -> dict:
        from ..models import OrderStatus

        history = list(order.status_history.order_by("created_at"))

        reached = {"created"}
        if order.status in (
            OrderStatus.NEW, OrderStatus.WAITING_SERVICE, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED,
        ):
            reached.add("matching")
        if order.assigned_supplier_id:
            reached.add("accepted")
        if order.scheduled_for or order.requested_date:
            reached.add("scheduled")
        if order.started_at:
            reached.add("started")
        if order.completed_at:
            reached.add("completed")

        cancelled = order.status == OrderStatus.CANCELLED
        steps = [{"key": key, "label": label, "reached": key in reached} for key, label in TIMELINE_STEPS]
        return {"steps": steps, "history": history, "cancelled": cancelled}
