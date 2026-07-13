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
    path("financial/escrows/", views.escrow_overview, name="escrow-overview"),
    path("financial/escrows/<uuid:escrow_id>/", views.escrow_detail, name="escrow-detail"),
    path("financial/disputes/", views.dispute_queue, name="dispute-queue"),
    path("financial/disputes/<uuid:dispute_id>/", views.dispute_detail, name="dispute-detail"),
    path("financial/disputes/<uuid:dispute_id>/resolve/", views.dispute_resolve_action, name="dispute-resolve"),
    path("financial/instructions/", views.release_refund_overview, name="release-refund-overview"),
    path("financial/feature-gates/", views.feature_gate_overview, name="feature-gate-overview"),
    path("system/", views.system_status, name="system-status"),
]
