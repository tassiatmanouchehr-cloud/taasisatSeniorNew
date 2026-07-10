"""
Organization portal views — Epic 02 (Marketplace Operational Experience).

Every view: authenticate -> resolve the caller's own OrganizationProfile ->
call service methods -> render a template. No ORM access of any kind
(enforced by OrganizationPortalOrmDisciplineTest, mirroring
apps.kernel.tests.test_architecture_guardrails.PortalOrmDisciplineTest).
"""

from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.services.errors import AccountsError
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.availability.services.capacity_service import CapacityService
from apps.booking.services.organization_assignment import OrganizationAssignmentError, OrganizationAssignmentService
from apps.notifications.services.queries import NotificationQueryService
from apps.orders.services.queries import OrderQueryService
from apps.reporting.services.provider_report_service import ProviderReportService

from .forms import AssignStaffForm
from .permissions import require_authenticated, resolve_organization, resolve_tenant_id

RECENT_NOTIFICATIONS_LIMIT = 5


def _guard(request):
    require_authenticated(request)
    tenant_id = resolve_tenant_id(request)
    organization = resolve_organization(request)
    return organization, tenant_id


# ============================================================
# Dashboard
# ============================================================

@require_http_methods(["GET"])
def dashboard_view(request):
    organization, tenant_id = _guard(request)

    staff_total = OrganizationStaffService.count_staff(organization)
    staff_pending = OrganizationStaffService.count_pending_staff(organization)
    open_orders = OrderQueryService.list_recent_unassigned_for_tenant(tenant_id=tenant_id, limit=5)
    open_orders_count = OrderQueryService.count_unassigned_for_tenant(tenant_id=tenant_id)

    recent_notifications = NotificationQueryService.list_recent_for_recipient(
        tenant_id=tenant_id, recipient_id=request.user.person_id, limit=RECENT_NOTIFICATIONS_LIMIT,
    )
    unread_notification_count = NotificationQueryService.count_unread_for_recipient(
        tenant_id=tenant_id, recipient_id=request.user.person_id,
    )

    context = {
        "organization": organization,
        "staff_total": staff_total,
        "staff_pending": staff_pending,
        "open_orders": open_orders,
        "open_orders_count": open_orders_count,
        "recent_notifications": recent_notifications,
        "unread_notification_count": unread_notification_count,
    }
    return render(request, "organization_portal/dashboard.html", context)


# ============================================================
# Staff management
# ============================================================

@require_http_methods(["GET"])
def staff_list_view(request):
    organization, tenant_id = _guard(request)
    staff = OrganizationStaffService.list_staff(organization)
    return render(request, "organization_portal/staff_list.html", {"staff": staff})


@require_http_methods(["POST"])
def staff_approve_view(request, membership_id):
    organization, tenant_id = _guard(request)
    try:
        membership = OrganizationStaffService.get_membership(organization=organization, membership_id=membership_id)
    except AccountsError:
        raise Http404("Staff member not found.")

    OrganizationStaffService.approve_membership(membership, approved_by=request.user)
    return redirect("organization_portal:staff")


@require_http_methods(["POST"])
def staff_suspend_view(request, membership_id):
    organization, tenant_id = _guard(request)
    try:
        membership = OrganizationStaffService.get_membership(organization=organization, membership_id=membership_id)
    except AccountsError:
        raise Http404("Staff member not found.")

    OrganizationStaffService.suspend_membership(membership)
    return redirect("organization_portal:staff")


# ============================================================
# Assignment center
# ============================================================

@require_http_methods(["GET"])
def assignment_center_view(request):
    organization, tenant_id = _guard(request)

    open_orders = OrderQueryService.list_unassigned_for_tenant(tenant_id=tenant_id)
    available_staff = OrganizationStaffService.list_active_caregivers(organization)

    return render(request, "organization_portal/assignment_center.html", {
        "open_orders": open_orders, "available_staff": available_staff, "form": AssignStaffForm(),
    })


@require_http_methods(["POST"])
def assign_staff_view(request, order_id):
    organization, tenant_id = _guard(request)

    form = AssignStaffForm(request.POST)
    if form.is_valid():
        try:
            OrganizationAssignmentService.assign_manual(
                organization=organization, order_id=order_id,
                membership_id=form.cleaned_data["membership_id"], actor=request.user,
            )
        except OrganizationAssignmentError as exc:
            return render(request, "organization_portal/action_error.html", {"error": str(exc)})

    return redirect("organization_portal:assignment-center")


# ============================================================
# Capacity overview
# ============================================================

@require_http_methods(["GET"])
def capacity_view(request):
    organization, tenant_id = _guard(request)

    rows = []
    for membership in OrganizationStaffService.list_active_caregivers(organization):
        try:
            supplier = resolve_supplier_for_user(membership.user)
        except AccountsError:
            continue
        rows.append({
            "membership": membership,
            "engagement_count": CapacityService.get_active_engagement_count(supplier=supplier),
            "capacity_exceeded": CapacityService.is_capacity_exceeded(supplier=supplier),
        })

    return render(request, "organization_portal/capacity.html", {"rows": rows})


# ============================================================
# Reports
# ============================================================

@require_http_methods(["GET"])
def reports_view(request):
    organization, tenant_id = _guard(request)

    supplier_ids = OrganizationStaffService.list_active_caregiver_supplier_ids(organization)
    reports = ProviderReportService.list_reports_for_suppliers(tenant_id, supplier_ids)

    return render(request, "organization_portal/reports.html", {"reports": reports})


# ============================================================
# Notification center
# ============================================================

@require_http_methods(["GET"])
def notifications_view(request):
    organization, tenant_id = _guard(request)

    filter_param = request.GET.get("filter", "all")
    only = filter_param if filter_param in ("unread", "read") else None
    notifications = NotificationQueryService.list_for_recipient(
        tenant_id=tenant_id, recipient_id=request.user.person_id, only=only,
    )

    return render(request, "organization_portal/notifications.html", {
        "notifications": notifications, "filter": filter_param,
    })
