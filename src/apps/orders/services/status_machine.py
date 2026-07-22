"""Order status machine — transitions, assignment, cancellation."""

from django.db import transaction
from django.utils import timezone

from apps.kernel.permissions.keys import ORDERS_CANCELLATION_APPROVE, ORDERS_CANCELLATION_REQUEST
from apps.kernel.services.permission_service import PermissionService

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
        tenant_id=order.tenant_id,
        from_status=from_status,
        to_status=to_status,
        changed_by=changed_by,
        reason=reason,
    )


@transaction.atomic
def approve_public_order(*, order_id, reviewed_by, assigned_supplier=None):
    """
    Approve a public order (pending_operator_review → new or waiting_service).
    """
    order = Order.objects.select_for_update().get(id=order_id)
    if order.status != OrderStatus.PENDING_OPERATOR_REVIEW:
        raise OrderStateError("فقط سفارش‌های در انتظار تایید قابل تایید هستند.")

    order.reviewed_by = reviewed_by
    order.approved_at = timezone.now()

    if assigned_supplier:
        order.assigned_supplier = assigned_supplier
        to_status = OrderStatus.WAITING_SERVICE
    else:
        to_status = OrderStatus.NEW

    order.status = to_status
    order.save(update_fields=["status", "reviewed_by", "approved_at", "assigned_supplier", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        tenant_id=order.tenant_id,
        from_status=OrderStatus.PENDING_OPERATOR_REVIEW,
        to_status=to_status,
        changed_by=reviewed_by,
        reason="تایید توسط اپراتور",
    )
    return order


@transaction.atomic
def assign_supplier(*, order_id, supplier, changed_by=None):
    """Assign supplier → waiting_service."""
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)

    from_status = order.status
    order.assigned_supplier = supplier
    order.status = OrderStatus.WAITING_SERVICE
    order.save(update_fields=["status", "assigned_supplier", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        tenant_id=order.tenant_id,
        from_status=from_status,
        to_status=OrderStatus.WAITING_SERVICE,
        changed_by=changed_by,
        reason="تخصیص تامین‌کننده",
    )
    return order


@transaction.atomic
def remove_supplier(*, order_id, changed_by=None):
    """Remove supplier → new."""
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)

    from_status = order.status
    order.assigned_supplier = None
    order.status = OrderStatus.NEW
    order.save(update_fields=["status", "assigned_supplier", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        tenant_id=order.tenant_id,
        from_status=from_status,
        to_status=OrderStatus.NEW,
        changed_by=changed_by,
        reason="حذف تامین‌کننده",
    )
    return order


@transaction.atomic
def replace_supplier(*, order_id, new_supplier, changed_by=None):
    """Replace supplier → waiting_service."""
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)

    from_status = order.status
    order.assigned_supplier = new_supplier
    order.status = OrderStatus.WAITING_SERVICE
    order.save(update_fields=["status", "assigned_supplier", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        tenant_id=order.tenant_id,
        from_status=from_status,
        to_status=OrderStatus.WAITING_SERVICE,
        changed_by=changed_by,
        reason="جایگزینی تامین‌کننده",
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
def request_cancellation(*, order_id, requested_by, tenant_id=None, reason=""):
    """Any non-final status → cancellation_requested.

    Authorization: requires orders.cancellation.request permission.
    The actor (requested_by) is evaluated against the order's tenant.
    tenant_id is optional for backward compatibility — if not provided,
    it is derived from the order itself.
    """
    order = Order.objects.select_for_update().get(id=order_id)

    effective_tenant_id = tenant_id if tenant_id is not None else order.tenant_id

    # Authorization enforcement (Sprint 5.3A)
    # The actor pattern follows AssignmentService.assign(): actor=None,
    # ownership_authorized_by=requested_by. This means:
    # 1. If the user has an RBAC role with this key: authorized via RBAC
    # 2. If not: authorized via the ownership-authorized path (audited)
    # 3. The REAL authorization boundary is upstream — the calling view
    #    verifies the user owns/relates to this order before calling.
    PermissionService.require(
        None,
        ORDERS_CANCELLATION_REQUEST,
        tenant_id=effective_tenant_id,
        ownership_authorized_by=requested_by,
    )

    _ensure_not_final(order)
    if order.status == OrderStatus.CANCELLATION_REQUESTED:
        raise OrderStateError("درخواست لغو قبلاً ثبت شده است.")

    order.cancellation_requested_by = requested_by
    order.cancellation_reason = reason
    from_status = order.status
    order.status = OrderStatus.CANCELLATION_REQUESTED
    order.save(update_fields=["status", "cancellation_requested_by", "cancellation_reason", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        tenant_id=order.tenant_id,
        from_status=from_status,
        to_status=OrderStatus.CANCELLATION_REQUESTED,
        changed_by=requested_by,
        reason=reason or "درخواست لغو",
    )
    return order


@transaction.atomic
def approve_cancellation(*, order_id, changed_by=None, tenant_id=None):
    """cancellation_requested → cancelled.

    Authorization: requires orders.cancellation.approve permission.
    The actor (changed_by) is evaluated against the order's tenant.
    tenant_id is optional for backward compatibility — if not provided,
    it is derived from the order itself.
    """
    order = Order.objects.select_for_update().get(id=order_id)

    effective_tenant_id = tenant_id if tenant_id is not None else order.tenant_id

    # Authorization enforcement (Sprint 5.3A)
    # Same pattern as request_cancellation: actor=None,
    # ownership_authorized_by=changed_by. When changed_by=None (system
    # context, e.g. background job), both are None → audited system path.
    PermissionService.require(
        None,
        ORDERS_CANCELLATION_APPROVE,
        tenant_id=effective_tenant_id,
        ownership_authorized_by=changed_by,
    )

    if order.status != OrderStatus.CANCELLATION_REQUESTED:
        raise OrderStateError("فقط سفارش‌های با درخواست لغو قابل تایید لغو هستند.")

    order.cancelled_at = timezone.now()
    _transition(order, to_status=OrderStatus.CANCELLED, changed_by=changed_by, reason="تایید لغو")
    order.save(update_fields=["cancelled_at"])
    return order
