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

from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.organization_profile_service import OrganizationProfileUpdateService
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.accounts.services.profile_media_service import ProfileMediaService
from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
from apps.availability.services.capacity_service import CapacityService
from apps.booking.services.organization_assignment import OrganizationAssignmentError, OrganizationAssignmentService
from apps.booking.services.queries import ProviderAssignmentQueryService
from apps.commission.services.queries import FinancialCoreQueryService
from apps.notifications.services.queries import NotificationQueryService
from apps.orders.services.queries import OrderQueryService
from apps.reporting.services.provider_report_service import ProviderReportService

from .forms import (
    AssignStaffForm,
    OrganizationDocumentUploadForm,
    OrganizationImageUploadForm,
    OrganizationProfileForm,
    OrganizationServicesForm,
)
from .permissions import require_authenticated, resolve_organization, resolve_tenant_id
from .services.profile_service import (
    DOCUMENT_TYPE_LABELS,
    ORGANIZATION_DOCUMENT_TYPES,
    OrganizationProfilePresentationService,
)

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
    open_orders = OrderQueryService.list_recent_eligible_for_organization(
        organization=organization,
        tenant_id=tenant_id,
        limit=5,
    )
    open_orders_count = OrderQueryService.count_eligible_for_organization(
        organization=organization, tenant_id=tenant_id
    )

    recent_notifications = NotificationQueryService.list_recent_for_recipient(
        tenant_id=tenant_id,
        recipient_id=request.user.person_id,
        limit=RECENT_NOTIFICATIONS_LIMIT,
    )
    unread_notification_count = NotificationQueryService.count_unread_for_recipient(
        tenant_id=tenant_id,
        recipient_id=request.user.person_id,
    )

    context = {
        "organization": organization,
        "staff_total": staff_total,
        "staff_pending": staff_pending,
        "open_orders": open_orders,
        "open_orders_count": open_orders_count,
        "recent_notifications": recent_notifications,
        "unread_notification_count": unread_notification_count,
        "nav_items": OrganizationProfilePresentationService.build_nav_items(active="dashboard"),
    }
    return render(request, "organization_portal/dashboard.html", context)


# ============================================================
# Staff management
# ============================================================


@require_http_methods(["GET"])
def staff_list_view(request):
    organization, tenant_id = _guard(request)
    staff = OrganizationStaffService.list_staff(organization)
    return render(
        request,
        "organization_portal/staff_list.html",
        {
            "staff": staff,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="staff"),
        },
    )


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

    OrganizationStaffService.suspend_membership(membership, suspended_by=request.user)
    return redirect("organization_portal:staff")


# ============================================================
# Assignment center
# ============================================================


@require_http_methods(["GET"])
def assignment_center_view(request):
    organization, tenant_id = _guard(request)

    open_orders = OrderQueryService.list_eligible_for_organization(organization=organization, tenant_id=tenant_id)
    available_staff = OrganizationStaffService.list_active_caregivers(organization)

    return render(
        request,
        "organization_portal/assignment_center.html",
        {
            "open_orders": open_orders,
            "available_staff": available_staff,
            "form": AssignStaffForm(),
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="assignment-center"),
        },
    )


@require_http_methods(["POST"])
def assign_staff_view(request, order_id):
    organization, tenant_id = _guard(request)

    form = AssignStaffForm(request.POST)
    if form.is_valid():
        try:
            OrganizationAssignmentService.assign_manual(
                organization=organization,
                order_id=order_id,
                membership_id=form.cleaned_data["membership_id"],
                actor=request.user,
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
        rows.append(
            {
                "membership": membership,
                "engagement_count": CapacityService.get_active_engagement_count(supplier=supplier),
                "capacity_exceeded": CapacityService.is_capacity_exceeded(supplier=supplier),
            }
        )

    return render(
        request,
        "organization_portal/capacity.html",
        {
            "rows": rows,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="capacity"),
        },
    )


# ============================================================
# Reports
# ============================================================


@require_http_methods(["GET"])
def reports_view(request):
    organization, tenant_id = _guard(request)

    supplier_ids = OrganizationStaffService.list_active_caregiver_supplier_ids(organization)
    reports = ProviderReportService.list_reports_for_suppliers(tenant_id, supplier_ids)

    return render(
        request,
        "organization_portal/reports.html",
        {
            "reports": reports,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="reports"),
        },
    )


# ============================================================
# Financial Core PR-B — organization-scoped Escrow/dispute status
# (Section 24 minimal organization-portal UI)
# ============================================================


@require_http_methods(["GET"])
def financial_view(request):
    """GET /organization/financial/ — held/disputed/releasable status for
    orders assigned directly to this organization's own ServiceSupplier.
    Read-only; does not cover orders assigned to individually-affiliated
    caregivers (a full affiliated-caregiver fan-out is out of scope for
    this minimal PR-B view)."""
    organization, tenant_id = _guard(request)

    org_supplier = get_or_create_supplier_for_organization(organization, tenant_id=tenant_id)
    assignments = ProviderAssignmentQueryService.list_for_supplier(supplier=org_supplier, tenant_id=tenant_id)

    rows = [
        {
            "order": assignment.order,
            "financial": FinancialCoreQueryService.get_order_financial_view(
                tenant_id=tenant_id,
                order=assignment.order,
            ),
        }
        for assignment in assignments
    ]
    rows = [row for row in rows if row["financial"].escrow_exists]

    return render(
        request,
        "organization_portal/financial.html",
        {
            "rows": rows,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="financial"),
        },
    )


# ============================================================
# Notification center
# ============================================================


@require_http_methods(["GET"])
def notifications_view(request):
    organization, tenant_id = _guard(request)

    filter_param = request.GET.get("filter", "all")
    only = filter_param if filter_param in ("unread", "read") else None
    notifications = NotificationQueryService.list_for_recipient(
        tenant_id=tenant_id,
        recipient_id=request.user.person_id,
        only=only,
    )

    return render(
        request,
        "organization_portal/notifications.html",
        {
            "notifications": notifications,
            "filter": filter_param,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="notifications"),
        },
    )


# ============================================================
# Self-profile — Epic 06 Sprint 2
# ============================================================


@require_http_methods(["GET"])
def profile_view(request):
    organization, tenant_id = _guard(request)
    profile = OrganizationProfilePresentationService.get_profile_view(organization=organization, tenant_id=tenant_id)
    return render(
        request,
        "organization_portal/profile.html",
        {
            "profile": profile,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_edit_view(request):
    organization, tenant_id = _guard(request)
    current = OrganizationProfilePresentationService.get_profile_form(organization)
    form = OrganizationProfileForm(
        request.POST or None,
        initial={
            "name": current.name,
            "description": current.description,
            "city": current.city,
            "phone": current.phone,
            "address": current.address,
            "company_type": current.company_type,
            "team_size": current.team_size,
        },
    )
    if request.method == "POST" and form.is_valid():
        OrganizationProfileUpdateService.update_profile(
            organization,
            actor=request.user,
            name=form.cleaned_data["name"],
            description=form.cleaned_data["description"],
            city=form.cleaned_data["city"],
            phone=form.cleaned_data["phone"],
            address=form.cleaned_data["address"],
            company_type=form.cleaned_data["company_type"],
            team_size=form.cleaned_data["team_size"],
        )
        return redirect("organization_portal:profile")
    return render(
        request,
        "organization_portal/profile_edit.html",
        {
            "form": form,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_edit_services_view(request):
    organization, tenant_id = _guard(request)
    services = OrganizationProfilePresentationService.get_services_form(organization, tenant_id=tenant_id)
    choices = [(opt.value, opt.label) for opt in services.service_category_options]
    selected = [opt.value for opt in services.service_category_options if opt.selected]

    form = OrganizationServicesForm(
        request.POST or None,
        initial={"service_category_ids": selected},
        service_category_choices=choices,
    )
    if request.method == "POST" and form.is_valid():
        OrganizationProfileUpdateService.update_service_categories(
            organization,
            actor=request.user,
            service_category_ids=form.cleaned_data["service_category_ids"],
        )
        return redirect("organization_portal:profile")
    return render(
        request,
        "organization_portal/profile_edit_services.html",
        {
            "form": form,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def logo_upload_view(request):
    organization, tenant_id = _guard(request)
    form = OrganizationImageUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            ProfileMediaService.set_organization_logo(organization, form.cleaned_data["image"])
        except AccountsError as exc:
            form.add_error("image", str(exc))
        else:
            return redirect("organization_portal:profile")
    return render(
        request,
        "organization_portal/media_upload.html",
        {
            "form": form,
            "title": "لوگوی سازمان",
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["POST"])
def logo_remove_view(request):
    organization, tenant_id = _guard(request)
    ProfileMediaService.remove_organization_logo(organization)
    return redirect("organization_portal:profile")


@require_http_methods(["GET", "POST"])
def cover_upload_view(request):
    organization, tenant_id = _guard(request)
    form = OrganizationImageUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            ProfileMediaService.set_organization_cover(organization, form.cleaned_data["image"])
        except AccountsError as exc:
            form.add_error("image", str(exc))
        else:
            return redirect("organization_portal:profile")
    return render(
        request,
        "organization_portal/media_upload.html",
        {
            "form": form,
            "title": "تصویر کاور سازمان",
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["POST"])
def cover_remove_view(request):
    organization, tenant_id = _guard(request)
    ProfileMediaService.remove_organization_cover(organization)
    return redirect("organization_portal:profile")


@require_http_methods(["GET", "POST"])
def document_manage_view(request, document_type):
    organization, tenant_id = _guard(request)
    if document_type not in ORGANIZATION_DOCUMENT_TYPES:
        raise Http404("Unknown document type.")

    existing = DocumentService.list_for_organization(organization).filter(document_type=document_type).first()
    form = OrganizationDocumentUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            if existing is not None:
                DocumentService.resubmit(existing, actor=request.user, file=form.cleaned_data["file"])
            else:
                DocumentService.upload_organization_document(
                    organization,
                    document_type=document_type,
                    file=form.cleaned_data["file"],
                )
        except AccountsError as exc:
            form.add_error("file", str(exc))
        else:
            return redirect("organization_portal:profile")

    return render(
        request,
        "organization_portal/document_upload.html",
        {
            "form": form,
            "label": DOCUMENT_TYPE_LABELS[document_type],
            "existing": existing,
            "nav_items": OrganizationProfilePresentationService.build_nav_items(active="profile"),
        },
    )
