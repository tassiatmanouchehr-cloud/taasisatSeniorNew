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
    path("verification/documents/", views.document_verification_queue, name="document-verification-queue"),
    path(
        "verification/documents/<uuid:document_id>/",
        views.document_verification_detail,
        name="document-verification-detail",
    ),
    path(
        "verification/documents/<uuid:document_id>/file/",
        views.document_verification_file,
        name="document-verification-file",
    ),
    path(
        "verification/documents/<uuid:document_id>/review/",
        views.document_verification_review_action,
        name="document-verification-review",
    ),
    path(
        "verification/caregivers/<uuid:caregiver_id>/",
        views.caregiver_activation_detail,
        name="caregiver-activation-detail",
    ),
    path(
        "verification/caregivers/<uuid:caregiver_id>/activate/",
        views.caregiver_activate_action,
        name="caregiver-activate",
    ),
    path(
        "verification/organizations/<uuid:organization_id>/",
        views.organization_activation_detail,
        name="organization-activation-detail",
    ),
    path(
        "verification/organizations/<uuid:organization_id>/activate/",
        views.organization_activate_action,
        name="organization-activate",
    ),
    path("system/", views.system_status, name="system-status"),
    path("system/rbac-enforcement/", views.rbac_enforcement_status, name="rbac-enforcement-status"),
]
