"""Order status machine — transitions, assignment, cancellation."""

from django.db import transaction
from django.utils import timezone

from ..models import FINAL_STATUSES, Order, OrderStatus, OrderStatusHistory


class OrderStateError(Exception):
    pass


def _ensure_not_final(order):
    """Raise if order is in a final (immutable) status."""
    if order.status in FINAL_STATUSES:
        raise OrderStateError(f"سفارش در وضعیت نهایی ({order.get_status_display()}) قابل تغییر نیست.")


def _transition(order, *, to_status, changed_by=None, reason=""):
    """Record status transition and update order."""
    from_status = order.status
    order.status = to_status
    order.save(update_fields=["status", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order,
        from_status=from_status,
        to_status=to_status,
        changed_by=changed_by,
        reason=reason,
    )


@transaction.atomic
def approve_public_order(*, order_id, reviewed_by, assigned_provider=None):
    """
    Approve a public order (pending_operator_review → new or waiting_service).
    """
    order = Order.objects.select_for_update().get(id=order_id)
    if order.status != OrderStatus.PENDING_OPERATOR_REVIEW:
        raise OrderStateError("فقط سفارش‌های در انتظار تایید قابل تایید هستند.")

    order.reviewed_by = reviewed_by
    order.approved_at = timezone.now()

    if assigned_provider:
        order.assigned_provider = assigned_provider
        to_status = OrderStatus.WAITING_SERVICE
    else:
        to_status = OrderStatus.NEW

    order.status = to_status
    order.save(update_fields=["status", "reviewed_by", "approved_at", "assigned_provider", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order, from_status=OrderStatus.PENDING_OPERATOR_REVIEW,
        to_status=to_status, changed_by=reviewed_by, reason="تایید توسط اپراتور",
    )
    return order


@transaction.atomic
def assign_provider(*, order_id, provider, changed_by=None):
    """Assign provider → waiting_service."""
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)

    order.assigned_provider = provider
    order.status = OrderStatus.WAITING_SERVICE
    order.save(update_fields=["status", "assigned_provider", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order, from_status=order.status, to_status=OrderStatus.WAITING_SERVICE,
        changed_by=changed_by, reason="تخصیص ارائه‌دهنده",
    )
    return order


@transaction.atomic
def remove_provider(*, order_id, changed_by=None):
    """Remove provider → new."""
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)

    from_status = order.status
    order.assigned_provider = None
    order.status = OrderStatus.NEW
    order.save(update_fields=["status", "assigned_provider", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order, from_status=from_status, to_status=OrderStatus.NEW,
        changed_by=changed_by, reason="حذف ارائه‌دهنده",
    )
    return order


@transaction.atomic
def replace_provider(*, order_id, new_provider, changed_by=None):
    """Replace provider → waiting_service."""
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)

    from_status = order.status
    order.assigned_provider = new_provider
    order.status = OrderStatus.WAITING_SERVICE
    order.save(update_fields=["status", "assigned_provider", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order, from_status=from_status, to_status=OrderStatus.WAITING_SERVICE,
        changed_by=changed_by, reason="جایگزینی ارائه‌دهنده",
    )
    return order


@transaction.atomic
def start_order(*, order_id, changed_by=None):
    """waiting_service → in_progress."""
    order = Order.objects.select_for_update().get(id=order_id)
    if order.status != OrderStatus.WAITING_SERVICE:
        raise OrderStateError("فقط سفارش‌های در انتظار انجام خدمت قابل شروع هستند.")

    order.started_at = timezone.now()
    _transition(order, to_status=OrderStatus.IN_PROGRESS, changed_by=changed_by, reason="شروع خدمت")
    order.save(update_fields=["started_at"])
    return order


@transaction.atomic
def complete_order(*, order_id, changed_by=None):
    """in_progress → completed."""
    order = Order.objects.select_for_update().get(id=order_id)
    if order.status != OrderStatus.IN_PROGRESS:
        raise OrderStateError("فقط سفارش‌های در حال انجام قابل تکمیل هستند.")

    order.completed_at = timezone.now()
    _transition(order, to_status=OrderStatus.COMPLETED, changed_by=changed_by, reason="اتمام خدمت")
    order.save(update_fields=["completed_at"])
    return order


@transaction.atomic
def request_cancellation(*, order_id, requested_by, reason=""):
    """Any non-final status → cancellation_requested."""
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)
    if order.status == OrderStatus.CANCELLATION_REQUESTED:
        raise OrderStateError("درخواست لغو قبلاً ثبت شده است.")

    order.cancellation_requested_by = requested_by
    order.cancellation_reason = reason
    from_status = order.status
    order.status = OrderStatus.CANCELLATION_REQUESTED
    order.save(update_fields=["status", "cancellation_requested_by", "cancellation_reason", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order, from_status=from_status, to_status=OrderStatus.CANCELLATION_REQUESTED,
        changed_by=requested_by, reason=reason or "درخواست لغو",
    )
    return order


@transaction.atomic
def approve_cancellation(*, order_id, changed_by=None):
    """cancellation_requested → cancelled."""
    order = Order.objects.select_for_update().get(id=order_id)
    if order.status != OrderStatus.CANCELLATION_REQUESTED:
        raise OrderStateError("فقط سفارش‌های با درخواست لغو قابل تایید لغو هستند.")

    order.cancelled_at = timezone.now()
    _transition(order, to_status=OrderStatus.CANCELLED, changed_by=changed_by, reason="تایید لغو")
    order.save(update_fields=["cancelled_at"])
    return order
