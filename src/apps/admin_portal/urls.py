"""/admin-portal/ routing — Module 19 foundation. Does not conflict with /admin/ or /api/v1/."""

from django.urls import path

from . import views

app_name = "admin_portal"

urlpatterns = [
    path("", views.portal_home, name="home"),
    path("tenants/", views.tenant_overview, name="tenant-overview"),
    path("suppliers/", views.supplier_overview, name="supplier-overview"),
    path("orders/", views.order_overview, name="order-overview"),
    path("finance/", views.finance_overview, name="finance-overview"),
    path("system/", views.system_status, name="system-status"),
]
