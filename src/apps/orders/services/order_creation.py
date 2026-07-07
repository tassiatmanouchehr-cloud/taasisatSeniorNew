"""Order creation services — public and operator intake paths."""

from django.db import transaction

from apps.kernel.services.tenant_service import TenantService

from ..models import (
    CatalogStatus,
    Order,
    OrderSource,
    OrderStatus,
    OrderStatusHistory,
    ServiceCategory,
    ServiceType,
)


class OrderValidationError(Exception):
    pass


def _validate_catalog(service_category_id, service_type_id=None, *, tenant_id):
    """Validate that category (and optional type) are active and tenant-scoped.

    A category/type belonging to a different tenant is treated the same as
    "not found" — this avoids leaking cross-tenant existence to callers.
    """
    try:
        category = ServiceCategory.objects.for_tenant(tenant_id).get(id=service_category_id)
    except ServiceCategory.DoesNotExist:
        raise OrderValidationError("دسته‌بندی خدمت یافت نشد.")

    if category.status != CatalogStatus.ACTIVE:
        raise OrderValidationError("دسته‌بندی خدمت غیرفعال است.")

    service_type = None
    if service_type_id:
        try:
            service_type = ServiceType.objects.for_tenant(tenant_id).get(id=service_type_id)
        except ServiceType.DoesNotExist:
            raise OrderValidationError("نوع خدمت یافت نشد.")
        if service_type.status != CatalogStatus.ACTIVE:
            raise OrderValidationError("نوع خدمت غیرفعال است.")

    return category, service_type


def _validate_required_fields(*, description, phone, address):
    """Validate required order fields."""
    if not description or not description.strip():
        raise OrderValidationError("توضیحات سفارش الزامی است.")
    if not phone or not phone.strip():
        raise OrderValidationError("شماره تماس الزامی است.")
    if not address or not address.strip():
        raise OrderValidationError("آدرس الزامی است.")


def _record_history(order, to_status, changed_by=None, reason=""):
    """Create an OrderStatusHistory entry."""
    OrderStatusHistory.objects.create(
        order=order,
        tenant_id=order.tenant_id,
        from_status="",
        to_status=to_status,
        changed_by=changed_by,
        reason=reason,
    )


@transaction.atomic
def create_public_order(
    *,
    service_category_id,
    description,
    phone,
    address,
    city="",
    service_type_id=None,
    customer_profile=None,
    elder_profile=None,
    trusted_contact=None,
    scheduled_for=None,
    requested_date=None,
    requested_time_window="",
    created_by=None,
    tenant_id=None,
):
    """
    Create a public/customer order.
    Initial status: pending_operator_review.
    """
    tenant_id = tenant_id or TenantService.get_default_tenant_id()
    _validate_required_fields(description=description, phone=phone, address=address)
    category, service_type = _validate_catalog(service_category_id, service_type_id, tenant_id=tenant_id)

    order = Order.objects.create(
        tenant_id=tenant_id,
        source=OrderSource.PUBLIC,
        status=OrderStatus.PENDING_OPERATOR_REVIEW,
        service_category=category,
        service_type=service_type,
        description=description,
        phone=phone,
        address=address,
        city=city,
        customer_profile=customer_profile,
        elder_profile=elder_profile,
        trusted_contact=trusted_contact,
        scheduled_for=scheduled_for,
        requested_date=requested_date,
        requested_time_window=requested_time_window,
        created_by=created_by,
    )

    _record_history(order, OrderStatus.PENDING_OPERATOR_REVIEW, changed_by=created_by, reason="سفارش عمومی ایجاد شد")
    return order


@transaction.atomic
def create_operator_order(
    *,
    service_category_id,
    description,
    phone,
    address,
    city="",
    service_type_id=None,
    customer_profile=None,
    elder_profile=None,
    assigned_supplier=None,
    scheduled_for=None,
    requested_date=None,
    requested_time_window="",
    internal_note="",
    created_by=None,
    tenant_id=None,
):
    """
    Create an operator/phone order.
    If assigned_supplier → waiting_service, else → new.
    """
    tenant_id = tenant_id or TenantService.get_default_tenant_id()
    _validate_required_fields(description=description, phone=phone, address=address)
    category, service_type = _validate_catalog(service_category_id, service_type_id, tenant_id=tenant_id)

    if assigned_supplier:
        status = OrderStatus.WAITING_SERVICE
    else:
        status = OrderStatus.NEW

    order = Order.objects.create(
        tenant_id=tenant_id,
        source=OrderSource.OPERATOR,
        status=status,
        service_category=category,
        service_type=service_type,
        description=description,
        phone=phone,
        address=address,
        city=city,
        customer_profile=customer_profile,
        elder_profile=elder_profile,
        assigned_supplier=assigned_supplier,
        scheduled_for=scheduled_for,
        requested_date=requested_date,
        requested_time_window=requested_time_window,
        internal_note=internal_note,
        created_by=created_by,
    )

    _record_history(order, status, changed_by=created_by, reason="سفارش اپراتوری ایجاد شد")
    return order
