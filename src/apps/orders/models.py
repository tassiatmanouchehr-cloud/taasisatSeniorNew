"""
Service Catalog and Order models.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.managers import TenantScopedManager


# ============================================================
# Service Catalog
# ============================================================

class CatalogStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class ServiceCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="service_categories",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=CatalogStatus.choices, default=CatalogStatus.ACTIVE)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_service_category"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Service Categories"
        unique_together = [("tenant", "slug")]

    def __str__(self):
        return self.name


class ServiceType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="service_types",
    )
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="service_types")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    base_duration_minutes = models.IntegerField(null=True, blank=True)
    requires_elder_profile = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=CatalogStatus.choices, default=CatalogStatus.ACTIVE)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_service_type"
        ordering = ["sort_order", "name"]
        unique_together = [("tenant", "category", "slug")]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


# ============================================================
# Order
# ============================================================

class OrderSource(models.TextChoices):
    PUBLIC = "public", "Public/Customer"
    OPERATOR = "operator", "Operator/Phone"


class OrderStatus(models.TextChoices):
    PENDING_OPERATOR_REVIEW = "pending_operator_review", "در انتظار تایید اپراتور"
    NEW = "new", "جدید"
    WAITING_SERVICE = "waiting_service", "در انتظار انجام خدمت"
    IN_PROGRESS = "in_progress", "در حال انجام خدمت"
    COMPLETED = "completed", "انجام شده"
    CANCELLATION_REQUESTED = "cancellation_requested", "درخواست لغو"
    CANCELLED = "cancelled", "لغو شده"


FINAL_STATUSES = {OrderStatus.COMPLETED, OrderStatus.CANCELLED}


def _generate_order_number():
    """Generate a human-readable order number: ORD-YYYYMMDD-XXXX."""
    from django.utils.crypto import get_random_string
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = get_random_string(4, "0123456789").upper()
    return f"ORD-{date_part}-{random_part}"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="orders",
    )
    order_number = models.CharField(max_length=30, unique=True, db_index=True)
    source = models.CharField(max_length=20, choices=OrderSource.choices)
    status = models.CharField(max_length=30, choices=OrderStatus.choices, db_index=True)

    # Customer/Elder
    customer_profile = models.ForeignKey(
        "accounts.CustomerProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders",
    )
    elder_profile = models.ForeignKey(
        "accounts.ElderProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders",
    )
    trusted_contact = models.ForeignKey(
        "accounts.TrustedContact", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders",
    )

    # Service
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="orders")
    service_type = models.ForeignKey(ServiceType, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")

    # Details
    description = models.TextField()
    city = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    requested_date = models.DateField(null=True, blank=True)
    requested_time_window = models.CharField(max_length=100, blank=True)

    # Assignment — ServiceSupplier is the single source of truth.
    # See assigned_provider/assigned_organization properties below for
    # read-only, backward-compatible access to the resolved profile.
    assigned_supplier = models.ForeignKey(
        "kernel.ServiceSupplier", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_orders",
    )

    # Actors
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_orders")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_orders")
    cancellation_requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    # Timestamps
    approved_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Notes
    cancellation_reason = models.TextField(blank=True)
    internal_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_number} [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _generate_order_number()
        super().save(*args, **kwargs)

    @property
    def assigned_provider(self):
        """Read-only: the CaregiverProfile behind assigned_supplier, if any.

        Kept for backward compatibility. ServiceSupplier (assigned_supplier)
        is the only writable assignment field on Order.
        """
        from apps.accounts.models import CaregiverProfile
        from apps.accounts.services.supplier_bridge import resolve_supplier_entity

        entity = resolve_supplier_entity(self.assigned_supplier)
        return entity if isinstance(entity, CaregiverProfile) else None

    @property
    def assigned_organization(self):
        """Read-only: the OrganizationProfile behind assigned_supplier, if any.

        Kept for backward compatibility. ServiceSupplier (assigned_supplier)
        is the only writable assignment field on Order.
        """
        from apps.accounts.models import OrganizationProfile
        from apps.accounts.services.supplier_bridge import resolve_supplier_entity

        entity = resolve_supplier_entity(self.assigned_supplier)
        return entity if isinstance(entity, OrganizationProfile) else None


class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="order_status_history",
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_status_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} → {self.to_status}"
