"""
Provider portal views — Epic 02 (Marketplace Operational Experience).

Every view: authenticate -> resolve the caller's own ServiceSupplier ->
call service methods -> render a template. No ORM access of any kind
(enforced by ProviderPortalOrmDisciplineTest, mirroring
apps.kernel.tests.test_architecture_guardrails.PortalOrmDisciplineTest).

Assignment-confirmation orchestration note: confirming an assignment
(apps.booking.services.provider_actions.ProviderAssignmentActionService
.confirm) and creating the ExecutionSession that follows from it
(apps.execution.services.session_service.ExecutionService.create_session)
are two separate service calls made here, in that order, rather than one
call inside apps.booking. apps.execution already depends on apps.booking
(imports its models); apps.booking must never import apps.execution back —
seedocs/architecture/dependency-graph.md. This view is the orchestration
point precisely because apps.provider_portal sits above both in the
dependency graph, the same role apps.portal already plays for
accounts/orders/finance/wallet/notifications/pricing.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.services.caregiver_profile_service import CaregiverProfileUpdateService
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.profile_media_service import ProfileMediaService
from apps.availability.services.capacity_service import CapacityService
from apps.availability.services.errors import AvailabilityError
from apps.availability.services.mutation_service import AvailabilityMutationService
from apps.availability.services.query_service import AvailabilityQueryService
from apps.booking.services.provider_actions import ProviderAssignmentActionError, ProviderAssignmentActionService
from apps.booking.services.queries import ProviderAssignmentNotFoundError, ProviderAssignmentQueryService
from apps.commission.services.queries import FinancialCoreQueryService
from apps.execution.models import ExecutionSource
from apps.execution.services.provider_actions import ProviderExecutionActionError, ProviderExecutionService
from apps.execution.services.queries import ProviderExecutionQueryService
from apps.execution.services.session_service import ExecutionService
from apps.finance.services.party_service import FinancialPartyService
from apps.notifications.services.queries import NotificationQueryService
from apps.reporting.services.provider_report_service import ProviderReportService
from apps.reviews.services.reputation_service import ReputationService
from apps.wallet.services.wallet_service import WalletService

from .forms import (
    BasicInfoForm,
    BlockedPeriodForm,
    DeclineAssignmentForm,
    DocumentUploadForm,
    ImageUploadForm,
    ProfessionalInfoForm,
    WorkingWindowForm,
)
from .permissions import require_authenticated, resolve_supplier, resolve_tenant_id
from .services.profile_service import (
    DOCUMENT_TYPE_LABELS,
    PROVIDER_DOCUMENT_TYPES,
    ProviderProfilePresentationService,
)

COMPLETED_VISITS_LIMIT = 5
RECENT_NOTIFICATIONS_LIMIT = 5


def _guard(request):
    require_authenticated(request)
    tenant_id = resolve_tenant_id(request)
    supplier = resolve_supplier(request)
    return supplier, tenant_id


def _guard_with_caregiver(request):
    """Same as _guard(), plus the caller's own CaregiverProfile — needed
    by the profile pages, which edit CaregiverProfile fields directly
    (not reachable through the generic-by-design ServiceSupplier)."""
    supplier, tenant_id = _guard(request)
    caregiver = getattr(request.user, "caregiver_profile", None)
    if caregiver is None:
        raise PermissionDenied("This account has no provider profile.")
    return supplier, tenant_id, caregiver


# ============================================================
# Dashboard
# ============================================================


@require_http_methods(["GET"])
def dashboard_view(request):
    supplier, tenant_id = _guard(request)

    pending_assignments = ProviderAssignmentQueryService.list_for_supplier(
        supplier=supplier,
        tenant_id=tenant_id,
        only="pending",
    )
    active_visits = ProviderExecutionQueryService.list_active_for_supplier(supplier=supplier, tenant_id=tenant_id)
    completed_visits = ProviderExecutionQueryService.list_completed_for_supplier(
        supplier=supplier,
        tenant_id=tenant_id,
        limit=COMPLETED_VISITS_LIMIT,
    )
    working_windows = AvailabilityQueryService.get_working_windows(supplier=supplier)
    reputation = ReputationService.get_reputation_summary(supplier)
    performance = ProviderReportService.get_report_for_supplier(tenant_id, supplier.id)

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
        "supplier": supplier,
        "pending_assignments": pending_assignments,
        "active_visits": active_visits,
        "completed_visits": completed_visits,
        "working_windows": working_windows,
        "reputation": reputation,
        "performance": performance,
        "recent_notifications": recent_notifications,
        "unread_notification_count": unread_notification_count,
        "nav_items": ProviderProfilePresentationService.build_nav_items(active="dashboard"),
    }
    return render(request, "provider_portal/dashboard.html", context)


# ============================================================
# Assignments + visit detail
# ============================================================


@require_http_methods(["GET"])
def assignments_list_view(request):
    supplier, tenant_id = _guard(request)
    filter_param = request.GET.get("filter", "all")
    only = filter_param if filter_param in ("pending", "confirmed") else None
    assignments = ProviderAssignmentQueryService.list_for_supplier(supplier=supplier, tenant_id=tenant_id, only=only)
    return render(
        request,
        "provider_portal/assignments_list.html",
        {
            "assignments": assignments,
            "filter": filter_param,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="assignments"),
        },
    )


@require_http_methods(["GET"])
def assignment_detail_view(request, order_id):
    supplier, tenant_id = _guard(request)
    try:
        assignment = ProviderAssignmentQueryService.get_for_supplier(
            supplier=supplier,
            tenant_id=tenant_id,
            order_id=order_id,
        )
    except ProviderAssignmentNotFoundError:
        raise Http404("Assignment not found.")

    session = ProviderExecutionQueryService.get_for_order_and_supplier(
        order_id=order_id,
        supplier=supplier,
        tenant_id=tenant_id,
    )
    return render(
        request,
        "provider_portal/assignment_detail.html",
        {
            "assignment": assignment,
            "order": assignment.order,
            "session": session,
            "decline_form": DeclineAssignmentForm(),
            "financial_view": FinancialCoreQueryService.get_order_financial_view(
                tenant_id=tenant_id,
                order=assignment.order,
            ),
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="assignments"),
        },
    )


@require_http_methods(["POST"])
def assignment_confirm_view(request, order_id):
    supplier, tenant_id = _guard(request)
    try:
        assignment = ProviderAssignmentQueryService.get_for_supplier(
            supplier=supplier,
            tenant_id=tenant_id,
            order_id=order_id,
        )
    except ProviderAssignmentNotFoundError:
        raise Http404("Assignment not found.")

    try:
        assignment = ProviderAssignmentActionService.confirm(assignment_id=assignment.id, actor=request.user)
    except ProviderAssignmentActionError as exc:
        return render(request, "provider_portal/action_error.html", {"error": str(exc)})

    ExecutionService.create_session(
        supplier_assignment=assignment,
        execution_source=ExecutionSource.BOOKING,
        triggered_by=request.user,
    )
    return redirect("provider_portal:assignment-detail", order_id=order_id)


@require_http_methods(["POST"])
def assignment_decline_view(request, order_id):
    supplier, tenant_id = _guard(request)
    try:
        assignment = ProviderAssignmentQueryService.get_for_supplier(
            supplier=supplier,
            tenant_id=tenant_id,
            order_id=order_id,
        )
    except ProviderAssignmentNotFoundError:
        raise Http404("Assignment not found.")

    form = DeclineAssignmentForm(request.POST)
    reason = form.cleaned_data.get("reason", "") if form.is_valid() else ""

    try:
        ProviderAssignmentActionService.decline(assignment_id=assignment.id, actor=request.user, reason=reason)
    except ProviderAssignmentActionError as exc:
        return render(request, "provider_portal/action_error.html", {"error": str(exc)})

    return redirect("provider_portal:assignments")


# ============================================================
# Execution actions
# ============================================================


@require_http_methods(["POST"])
def visit_start_view(request, order_id):
    supplier, tenant_id = _guard(request)
    session = ProviderExecutionQueryService.get_for_order_and_supplier(
        order_id=order_id,
        supplier=supplier,
        tenant_id=tenant_id,
    )
    if session is None:
        raise Http404("Visit not found.")

    try:
        ProviderExecutionService.start_visit(session_id=session.id, actor=request.user)
    except ProviderExecutionActionError as exc:
        return render(request, "provider_portal/action_error.html", {"error": str(exc)})

    return redirect("provider_portal:assignment-detail", order_id=order_id)


@require_http_methods(["POST"])
def visit_complete_view(request, order_id):
    supplier, tenant_id = _guard(request)
    session = ProviderExecutionQueryService.get_for_order_and_supplier(
        order_id=order_id,
        supplier=supplier,
        tenant_id=tenant_id,
    )
    if session is None:
        raise Http404("Visit not found.")

    try:
        ProviderExecutionService.complete_visit(session_id=session.id, actor=request.user)
    except ProviderExecutionActionError as exc:
        return render(request, "provider_portal/action_error.html", {"error": str(exc)})

    return redirect("provider_portal:assignment-detail", order_id=order_id)


# ============================================================
# Availability management
# ============================================================


@require_http_methods(["GET", "POST"])
def availability_view(request):
    supplier, tenant_id = _guard(request)

    window_form = WorkingWindowForm()
    if request.method == "POST":
        window_form = WorkingWindowForm(request.POST)
        if window_form.is_valid():
            try:
                AvailabilityMutationService.add_working_window(
                    supplier=supplier,
                    day_of_week=int(window_form.cleaned_data["day_of_week"]),
                    start_time=window_form.cleaned_data["start_time"],
                    end_time=window_form.cleaned_data["end_time"],
                )
                return redirect("provider_portal:availability")
            except AvailabilityError as exc:
                window_form.add_error(None, str(exc))

    working_windows = AvailabilityQueryService.get_working_windows(supplier=supplier)
    blocked_periods = AvailabilityQueryService.get_blocked_periods(supplier=supplier)
    engagement_count = CapacityService.get_active_engagement_count(supplier=supplier)
    capacity_exceeded = CapacityService.is_capacity_exceeded(supplier=supplier)

    return render(
        request,
        "provider_portal/availability.html",
        {
            "window_form": window_form,
            "blocked_period_form": BlockedPeriodForm(),
            "working_windows": working_windows,
            "blocked_periods": blocked_periods,
            "engagement_count": engagement_count,
            "capacity_exceeded": capacity_exceeded,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="availability"),
        },
    )


@require_http_methods(["POST"])
def working_window_remove_view(request, window_id):
    supplier, tenant_id = _guard(request)
    window = AvailabilityQueryService.get_working_window_for_supplier(supplier=supplier, window_id=window_id)
    if window is None:
        raise Http404("Working window not found.")
    AvailabilityMutationService.remove_working_window(window_id=window.id)
    return redirect("provider_portal:availability")


@require_http_methods(["POST"])
def blocked_period_create_view(request):
    supplier, tenant_id = _guard(request)
    form = BlockedPeriodForm(request.POST)
    if form.is_valid():
        try:
            AvailabilityMutationService.add_blocked_period(
                supplier=supplier,
                start_at=form.cleaned_data["start_at"],
                end_at=form.cleaned_data["end_at"],
                reason=form.cleaned_data["reason"] or "OTHER",
                notes=form.cleaned_data.get("notes", ""),
            )
        except AvailabilityError as exc:
            return render(request, "provider_portal/action_error.html", {"error": str(exc)})
    return redirect("provider_portal:availability")


@require_http_methods(["POST"])
def blocked_period_remove_view(request, blocked_period_id):
    supplier, tenant_id = _guard(request)
    period = AvailabilityQueryService.get_blocked_period_for_supplier(
        supplier=supplier,
        blocked_period_id=blocked_period_id,
    )
    if period is None:
        raise Http404("Blocked period not found.")
    AvailabilityMutationService.remove_blocked_period(blocked_period_id=period.id)
    return redirect("provider_portal:availability")


# ============================================================
# Earnings summary
# ============================================================


@require_http_methods(["GET"])
def earnings_view(request):
    supplier, tenant_id = _guard(request)

    party = FinancialPartyService.resolve_party_for_supplier(supplier)
    wallet = WalletService.get_wallet_or_none(party=party)
    performance = ProviderReportService.get_report_for_supplier(tenant_id, supplier.id)

    return render(
        request,
        "provider_portal/earnings.html",
        {
            "wallet": wallet,
            "performance": performance,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="earnings"),
        },
    )


# ============================================================
# Notification center
# ============================================================


@require_http_methods(["GET"])
def notifications_view(request):
    supplier, tenant_id = _guard(request)

    filter_param = request.GET.get("filter", "all")
    only = filter_param if filter_param in ("unread", "read") else None
    notifications = NotificationQueryService.list_for_recipient(
        tenant_id=tenant_id,
        recipient_id=request.user.person_id,
        only=only,
    )

    return render(
        request,
        "provider_portal/notifications.html",
        {
            "notifications": notifications,
            "filter": filter_param,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="notifications"),
        },
    )


# ============================================================
# Self-profile — Epic 06 Sprint 2
# ============================================================


@require_http_methods(["GET"])
def profile_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    profile = ProviderProfilePresentationService.get_profile_view(
        supplier=supplier,
        caregiver=caregiver,
        tenant_id=tenant_id,
    )
    return render(
        request,
        "provider_portal/profile.html",
        {
            "profile": profile,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_edit_basic_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    form = BasicInfoForm(
        request.POST or None,
        initial={"display_name": caregiver.display_name, "city": caregiver.city},
    )
    if request.method == "POST" and form.is_valid():
        CaregiverProfileUpdateService.update_basic_info(
            caregiver,
            display_name=form.cleaned_data["display_name"],
            city=form.cleaned_data["city"],
        )
        return redirect("provider_portal:profile")
    return render(
        request,
        "provider_portal/profile_edit_basic.html",
        {
            "form": form,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_edit_professional_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    professional = ProviderProfilePresentationService.get_professional_info_form(
        caregiver=caregiver,
        supplier=supplier,
        tenant_id=tenant_id,
    )
    choices = [(opt.value, opt.label) for opt in professional.service_category_options]
    selected = [opt.value for opt in professional.service_category_options if opt.selected]

    form = ProfessionalInfoForm(
        request.POST or None,
        initial={
            "bio": caregiver.bio,
            "specialty": caregiver.specialty,
            "years_experience": caregiver.years_experience,
            "service_radius_km": caregiver.service_radius_km,
            "service_category_ids": selected,
        },
        service_category_choices=choices,
    )
    if request.method == "POST" and form.is_valid():
        CaregiverProfileUpdateService.update_professional_info(
            caregiver,
            bio=form.cleaned_data["bio"],
            specialty=form.cleaned_data["specialty"],
            years_experience=form.cleaned_data["years_experience"],
            service_radius_km=form.cleaned_data["service_radius_km"],
            service_category_ids=form.cleaned_data["service_category_ids"],
        )
        return redirect("provider_portal:profile")
    return render(
        request,
        "provider_portal/profile_edit_professional.html",
        {
            "form": form,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def avatar_upload_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    form = ImageUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            ProfileMediaService.set_caregiver_avatar(caregiver, form.cleaned_data["image"])
        except AccountsError as exc:
            form.add_error("image", str(exc))
        else:
            return redirect("provider_portal:profile")
    return render(
        request,
        "provider_portal/media_upload.html",
        {
            "form": form,
            "title": "تصویر پروفایل",
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["POST"])
def avatar_remove_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    ProfileMediaService.remove_caregiver_avatar(caregiver)
    return redirect("provider_portal:profile")


@require_http_methods(["GET", "POST"])
def cover_upload_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    form = ImageUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            ProfileMediaService.set_caregiver_cover(caregiver, form.cleaned_data["image"])
        except AccountsError as exc:
            form.add_error("image", str(exc))
        else:
            return redirect("provider_portal:profile")
    return render(
        request,
        "provider_portal/media_upload.html",
        {
            "form": form,
            "title": "تصویر کاور",
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["POST"])
def cover_remove_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    ProfileMediaService.remove_caregiver_cover(caregiver)
    return redirect("provider_portal:profile")


@require_http_methods(["GET", "POST"])
def document_manage_view(request, document_type):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    if document_type not in PROVIDER_DOCUMENT_TYPES:
        raise Http404("Unknown document type.")

    existing = DocumentService.list_for_caregiver(caregiver).filter(document_type=document_type).first()
    form = DocumentUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            if existing is not None:
                DocumentService.replace_document(existing, file=form.cleaned_data["file"])
            else:
                DocumentService.upload_caregiver_document(
                    caregiver,
                    document_type=document_type,
                    file=form.cleaned_data["file"],
                )
        except AccountsError as exc:
            form.add_error("file", str(exc))
        else:
            return redirect("provider_portal:profile")

    return render(
        request,
        "provider_portal/document_upload.html",
        {
            "form": form,
            "label": DOCUMENT_TYPE_LABELS[document_type],
            "existing": existing,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )
