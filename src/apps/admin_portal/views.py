"""
Admin portal views — Module 19 foundation.

Every view: check permission -> call exactly one existing service method ->
render a template. No business logic, no direct ORM aggregation — see
docs/architecture/api-guidelines.md's thin-controller rule (the same rule
this module follows, just for server-rendered HTML instead of DRF JSON).
Read-only throughout: nothing here writes to the database.
"""

from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.kernel.api.health import HealthCheckView
from apps.reporting.services import (
    FinancialReportService,
    MarketplaceReportService,
    OperationalReportService,
    ProviderReportService,
)

from . import permission_keys
from .permissions import require_admin_permission


@require_GET
def portal_home(request):
    """GET /admin-portal/ — landing page with links to each overview page."""
    require_admin_permission(request, permission_keys.PORTAL_ACCESS)
    return render(request, "admin_portal/home.html")


@require_GET
def tenant_overview(request):
    """GET /admin-portal/tenants/ — the caller's own tenant's marketplace composition."""
    tenant_id = require_admin_permission(request, permission_keys.TENANTS_READ)
    stats = MarketplaceReportService.get_marketplace_stats(tenant_id)
    return render(request, "admin_portal/tenant_overview.html", {"stats": stats})


@require_GET
def supplier_overview(request):
    """GET /admin-portal/suppliers/ — per-supplier performance for the caller's own tenant."""
    tenant_id = require_admin_permission(request, permission_keys.SUPPLIERS_READ)
    reports = ProviderReportService.list_reports(tenant_id)
    return render(request, "admin_portal/supplier_overview.html", {"reports": reports})


@require_GET
def order_overview(request):
    """GET /admin-portal/orders/ — order counts for the caller's own tenant."""
    tenant_id = require_admin_permission(request, permission_keys.ORDERS_READ)
    counts = OperationalReportService.get_order_counts(tenant_id)
    return render(request, "admin_portal/order_overview.html", {"counts": counts})


@require_GET
def finance_overview(request):
    """GET /admin-portal/finance/ — financial summary for the caller's own tenant."""
    tenant_id = require_admin_permission(request, permission_keys.FINANCE_READ)
    summary = FinancialReportService.get_financial_summary(tenant_id)
    return render(request, "admin_portal/finance_overview.html", {"summary": summary})


@require_GET
def system_status(request):
    """GET /admin-portal/system/ — DB/cache health, reusing the existing health-check logic."""
    require_admin_permission(request, permission_keys.SYSTEM_READ)
    health_view = HealthCheckView()
    context = {
        "db_status": health_view._check_db(),
        "cache_status": health_view._check_cache(),
    }
    return render(request, "admin_portal/system_status.html", context)
