"""Django admin for orders app."""

from django.contrib import admin

from .models import Order, OrderOffer, OrderStatusHistory, ServiceCategory, ServiceType


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "tenant_id", "status", "sort_order", "created_at"]
    list_filter = ["status", "tenant_id"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "slug", "tenant_id", "status", "base_duration_minutes", "sort_order"]
    list_filter = ["status", "category", "requires_elder_profile", "tenant_id"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "tenant_id",
        "source",
        "status",
        "service_category",
        "city",
        "phone",
        "assigned_supplier",
        "created_at",
    ]
    list_filter = ["status", "source", "city", "tenant_id"]
    search_fields = ["order_number", "phone", "description"]
    readonly_fields = [
        "id",
        "tenant_id",
        "order_number",
        "created_at",
        "updated_at",
        "approved_at",
        "started_at",
        "completed_at",
        "cancelled_at",
    ]


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["order", "tenant_id", "from_status", "to_status", "changed_by", "created_at"]
    list_filter = ["to_status", "tenant_id"]
    search_fields = ["order__order_number"]
    readonly_fields = ["id", "tenant_id", "created_at"]


@admin.register(OrderOffer)
class OrderOfferAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "supplier", "price_amount", "currency", "status", "tenant_id", "created_at"]
    list_filter = ["status", "currency", "tenant_id"]
    search_fields = ["order__order_number", "supplier__display_name"]
    readonly_fields = ["id", "tenant_id", "created_at", "updated_at", "selected_at", "hold_expires_at"]
