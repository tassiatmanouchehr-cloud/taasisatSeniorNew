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

from apps.accounts.services import affiliations as affiliation_services
from apps.accounts.services.caregiver_gallery_service import MAX_GALLERY_ITEMS_PER_CAREGIVER, CaregiverGalleryService
from apps.accounts.services.caregiver_professional_profile_service import (
    CaregiverExperienceService,
    CaregiverSkillService,
)
from apps.accounts.services.caregiver_profile_service import CaregiverProfileUpdateService
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.profile_media_service import ProfileMediaService
from apps.availability.models import PERSIAN_DAY_LABELS
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
    ExperienceForm,
    GalleryItemEditForm,
    GalleryUploadForm,
    ImageUploadForm,
    JoinCompanyCodeForm,
    ProfessionalInfoForm,
    SkillForm,
    WorkingWindowEditForm,
    WorkingWindowForm,
)
from .permissions import require_authenticated, resolve_supplier, resolve_tenant_id
from .services.dashboard_service import CaregiverDashboardPresentationService
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
    """Resolves the caller's own CaregiverProfile — needed by the
    self-profile/self-management pages (dashboard, profile, skills,
    experience, gallery, avatar/cover, documents, company affiliation),
    which must remain viewable/usable for a DRAFT caregiver (profile
    completion, itself required for activation eligibility, is edited
    through exactly these pages).

    Core Profile-ServiceSupplier Invariant Remediation: deliberately does
    NOT build on _guard() (which now requires a genuinely ACTIVE
    supplier and rejects otherwise) — resolves identity through
    resolve_provider_context_for_user() instead, which never creates a
    ServiceSupplier for a non-ACTIVE profile. `supplier` is None for a
    DRAFT/SUSPENDED/ARCHIVED caregiver; every caller of this guard must
    handle that instead of assuming a real ServiceSupplier."""
    require_authenticated(request)
    tenant_id = resolve_tenant_id(request)

    from apps.accounts.services.errors import AccountsError
    from apps.accounts.services.provider_identity import resolve_provider_context_for_user

    try:
        context = resolve_provider_context_for_user(request.user)
    except AccountsError:
        raise PermissionDenied("This account has no provider profile.")
    return context.supplier, tenant_id, context.caregiver


# ============================================================
# Dashboard
# ============================================================


@require_http_methods(["GET"])
def dashboard_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    if supplier is None:
        # Core Profile-ServiceSupplier Invariant Remediation: a caregiver
        # who has never reached ACTIVE has no assignments/visits/earnings
        # to show (those all require a real supplier), but the dashboard
        # is still a page they may land on and view — it renders a
        # pending-activation state instead of creating/faking a supplier.
        profile = ProviderProfilePresentationService.get_profile_view(
            supplier=None,
            caregiver=caregiver,
            tenant_id=tenant_id,
        )
        context = {
            "supplier": None,
            "display_name": caregiver.display_name,
            "profile": profile,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="dashboard"),
        }
        return render(request, "provider_portal/dashboard.html", context)

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

    dashboard = CaregiverDashboardPresentationService.build_for_supplier(
        supplier=supplier,
        tenant_id=tenant_id,
        caregiver=caregiver,
        reputation=reputation,
        performance=performance,
    )

    context = {
        "supplier": supplier,
        "display_name": caregiver.display_name,
        "pending_assignments": pending_assignments,
        "active_visits": active_visits,
        "completed_visits": completed_visits,
        "working_windows": working_windows,
        "reputation": reputation,
        "performance": performance,
        "recent_notifications": recent_notifications,
        "unread_notification_count": unread_notification_count,
        "dashboard": dashboard,
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
    public_summary_days = _public_summary_labels(supplier)

    return render(
        request,
        "provider_portal/availability.html",
        {
            "window_form": window_form,
            "window_edit_form": WorkingWindowEditForm(),
            "blocked_period_form": BlockedPeriodForm(),
            "working_windows": working_windows,
            "blocked_periods": blocked_periods,
            "engagement_count": engagement_count,
            "capacity_exceeded": capacity_exceeded,
            "public_summary_days": public_summary_days,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="availability"),
        },
    )


def _public_summary_labels(supplier) -> tuple[str, ...]:
    """Sprint 2.4: the same safe, summarized (day-labels only, never exact
    times) preview the public caregiver profile shows — see
    apps.public_site.services.profile_service.CaregiverPublicProfileService
    ._availability_summary(), which computes it identically from the same
    canonical apps.availability.services.query_service.AvailabilityQueryService
    .get_distinct_active_days()."""
    days = AvailabilityQueryService.get_distinct_active_days(supplier=supplier)
    return tuple(PERSIAN_DAY_LABELS[day] for day in days)


@require_http_methods(["POST"])
def working_window_remove_view(request, window_id):
    supplier, tenant_id = _guard(request)
    window = AvailabilityQueryService.get_working_window_for_supplier(supplier=supplier, window_id=window_id)
    if window is None:
        raise Http404("Working window not found.")
    AvailabilityMutationService.remove_working_window(window_id=window.id)
    return redirect("provider_portal:availability")


@require_http_methods(["POST"])
def working_window_update_view(request, window_id):
    supplier, tenant_id = _guard(request)
    window = AvailabilityQueryService.get_working_window_for_supplier(supplier=supplier, window_id=window_id)
    if window is None:
        raise Http404("Working window not found.")

    form = WorkingWindowEditForm(request.POST)
    if form.is_valid():
        try:
            AvailabilityMutationService.update_working_window(
                window_id=window.id,
                start_time=form.cleaned_data["start_time"],
                end_time=form.cleaned_data["end_time"],
            )
        except AvailabilityError as exc:
            return render(request, "provider_portal/action_error.html", {"error": str(exc)})
    return redirect("provider_portal:availability")


@require_http_methods(["POST"])
def working_window_toggle_view(request, window_id):
    supplier, tenant_id = _guard(request)
    window = AvailabilityQueryService.get_working_window_for_supplier(supplier=supplier, window_id=window_id)
    if window is None:
        raise Http404("Working window not found.")
    try:
        AvailabilityMutationService.toggle_working_window(window=window)
    except AvailabilityError as exc:
        return render(request, "provider_portal/action_error.html", {"error": str(exc)})
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


# ============================================================
# Company affiliation — Phase 3 Sprint 3.1 (Company Foundation and
# Caregiver Management)
# ============================================================


@require_http_methods(["GET"])
def company_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    active_membership = affiliation_services.get_active_membership_for_caregiver(caregiver)
    pending_invitations = affiliation_services.list_pending_invitations_for_caregiver(caregiver)
    affiliation_requests = affiliation_services.list_affiliation_requests_for_caregiver(caregiver)
    history = affiliation_services.list_membership_history_for_caregiver(caregiver)
    return render(
        request,
        "provider_portal/company.html",
        {
            "active_membership": active_membership,
            "pending_invitations": pending_invitations,
            "affiliation_requests": affiliation_requests,
            "history": history,
            "join_form": JoinCompanyCodeForm(),
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="company"),
        },
    )


@require_http_methods(["POST"])
def company_join_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    form = JoinCompanyCodeForm(request.POST)
    if form.is_valid():
        try:
            affiliation_services.submit_join_request(
                caregiver_profile=caregiver,
                code=form.cleaned_data["code"],
                tenant_id=tenant_id,
            )
        except AccountsError:
            pass
    return redirect("provider_portal:company")


@require_http_methods(["POST"])
def company_request_cancel_view(request, request_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        affiliation_services.cancel_affiliation_request(request_id=request_id, caregiver_profile=caregiver)
    except AccountsError:
        pass
    return redirect("provider_portal:company")


@require_http_methods(["POST"])
def company_invitation_accept_view(request, membership_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        affiliation_services.accept_invitation(membership_id=membership_id, caregiver_profile=caregiver)
    except AccountsError:
        pass
    return redirect("provider_portal:company")


@require_http_methods(["POST"])
def company_invitation_decline_view(request, membership_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        affiliation_services.decline_invitation(membership_id=membership_id, caregiver_profile=caregiver)
    except AccountsError:
        pass
    return redirect("provider_portal:company")


@require_http_methods(["POST"])
def company_leave_view(request, membership_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        affiliation_services.leave_organization(membership_id=membership_id, caregiver_profile=caregiver)
    except AccountsError:
        pass
    return redirect("provider_portal:company")


# ============================================================
# Skills — Phase 2.1 (Caregiver Professional Profile Foundation)
# ============================================================


@require_http_methods(["GET", "POST"])
def profile_skills_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    form = SkillForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            CaregiverSkillService.add_skill(caregiver, name=form.cleaned_data["name"])
        except AccountsError as exc:
            form.add_error("name", str(exc))
        else:
            return redirect("provider_portal:profile-skills")
    return render(
        request,
        "provider_portal/profile_skills.html",
        {
            "form": form,
            "skills": ProviderProfilePresentationService.get_skills_view(caregiver),
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["POST"])
def profile_skill_remove_view(request, skill_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        CaregiverSkillService.remove_skill(caregiver, skill_id=skill_id)
    except AccountsError:
        pass  # already removed / not owned — page still shows current state.
    return redirect("provider_portal:profile-skills")


@require_http_methods(["POST"])
def profile_skill_visibility_toggle_view(request, skill_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        CaregiverSkillService.toggle_visibility(caregiver, skill_id=skill_id)
    except AccountsError:
        pass  # not owned — page still shows current state.
    return redirect("provider_portal:profile-skills")


# ============================================================
# Experience — Phase 2.1 (Caregiver Professional Profile Foundation)
# ============================================================


@require_http_methods(["GET"])
def profile_experience_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    return render(
        request,
        "provider_portal/profile_experience.html",
        {
            "experience": ProviderProfilePresentationService.get_experience_view(caregiver),
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_experience_add_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    form = ExperienceForm(request.POST or None, initial={"is_visible": True})
    if request.method == "POST" and form.is_valid():
        try:
            CaregiverExperienceService.create(
                caregiver,
                title=form.cleaned_data["title"],
                organization_name=form.cleaned_data["organization_name"],
                description=form.cleaned_data["description"],
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
                is_current=form.cleaned_data["is_current"],
                is_visible=form.cleaned_data["is_visible"],
            )
        except AccountsError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("provider_portal:profile-experience")
    return render(
        request,
        "provider_portal/profile_experience_form.html",
        {
            "form": form,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_experience_edit_view(request, experience_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        entry = caregiver.experiences.get(id=experience_id)
    except caregiver.experiences.model.DoesNotExist:
        raise Http404("Experience entry not found.") from None

    form = ExperienceForm(
        request.POST or None,
        initial={
            "title": entry.title,
            "organization_name": entry.organization_name,
            "description": entry.description,
            "start_date": entry.start_date,
            "end_date": entry.end_date,
            "is_current": entry.is_current,
            "is_visible": entry.is_visible,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            CaregiverExperienceService.update(
                caregiver,
                experience_id=experience_id,
                title=form.cleaned_data["title"],
                organization_name=form.cleaned_data["organization_name"],
                description=form.cleaned_data["description"],
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
                is_current=form.cleaned_data["is_current"],
                is_visible=form.cleaned_data["is_visible"],
            )
        except AccountsError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("provider_portal:profile-experience")
    return render(
        request,
        "provider_portal/profile_experience_form.html",
        {
            "form": form,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["POST"])
def profile_experience_delete_view(request, experience_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        CaregiverExperienceService.delete(caregiver, experience_id=experience_id)
    except AccountsError:
        pass  # already removed / not owned — page still shows current state.
    return redirect("provider_portal:profile-experience")


# ============================================================
# Gallery — Sprint 2.2 (Caregiver Professional Profile: Gallery and
# Media Portfolio)
# ============================================================


@require_http_methods(["GET", "POST"])
def profile_gallery_view(request):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    form = GalleryUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            CaregiverGalleryService.add_item(
                caregiver,
                image=form.cleaned_data["image"],
                caption=form.cleaned_data["caption"],
                alt_text=form.cleaned_data["alt_text"],
            )
        except AccountsError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("provider_portal:profile-gallery")
    return render(
        request,
        "provider_portal/profile_gallery.html",
        {
            "form": form,
            "gallery_items": ProviderProfilePresentationService.get_gallery_view(caregiver),
            "gallery_count": caregiver.gallery_items.count(),
            "gallery_limit": MAX_GALLERY_ITEMS_PER_CAREGIVER,
            # Core Profile-ServiceSupplier Invariant Remediation: no
            # supplier yet for a non-ACTIVE caregiver — no public preview
            # exists to link to (they aren't publicly listed either).
            "public_preview_url": f"/find-a-caregiver/{supplier.id}/" if supplier is not None else "",
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_gallery_item_edit_view(request, item_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        item = caregiver.gallery_items.get(id=item_id)
    except caregiver.gallery_items.model.DoesNotExist:
        raise Http404("Gallery item not found.") from None

    form = GalleryItemEditForm(
        request.POST or None,
        initial={"caption": item.caption, "alt_text": item.alt_text, "is_visible": item.is_visible},
    )
    if request.method == "POST" and form.is_valid():
        try:
            CaregiverGalleryService.update_item(
                caregiver,
                item_id=item_id,
                caption=form.cleaned_data["caption"],
                alt_text=form.cleaned_data["alt_text"],
                is_visible=form.cleaned_data["is_visible"],
            )
        except AccountsError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("provider_portal:profile-gallery")
    return render(
        request,
        "provider_portal/profile_gallery_item_edit.html",
        {
            "form": form,
            "item": item,
            "nav_items": ProviderProfilePresentationService.build_nav_items(active="profile"),
        },
    )


@require_http_methods(["POST"])
def profile_gallery_item_remove_view(request, item_id):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    try:
        CaregiverGalleryService.remove_item(caregiver, item_id=item_id)
    except AccountsError:
        pass  # already removed / not owned — page still shows current state.
    return redirect("provider_portal:profile-gallery")


@require_http_methods(["POST"])
def profile_gallery_item_move_view(request, item_id, direction):
    supplier, tenant_id, caregiver = _guard_with_caregiver(request)
    if direction not in ("up", "down"):
        raise Http404("Unknown direction.")

    ids = [str(item.id) for item in CaregiverGalleryService.list_items(caregiver)]
    try:
        index = ids.index(str(item_id))
    except ValueError:
        return redirect("provider_portal:profile-gallery")  # not owned — silent no-op.

    swap_with = index - 1 if direction == "up" else index + 1
    if 0 <= swap_with < len(ids):
        ids[index], ids[swap_with] = ids[swap_with], ids[index]
        try:
            CaregiverGalleryService.reorder(caregiver, ordered_item_ids=ids)
        except AccountsError:
            pass
    return redirect("provider_portal:profile-gallery")


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
                DocumentService.resubmit(existing, actor=request.user, file=form.cleaned_data["file"])
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
