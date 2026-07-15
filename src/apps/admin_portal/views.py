"""
Admin portal views — Module 19 foundation.

Every view: check permission -> call exactly one existing service method ->
render a template. No business logic, no direct ORM aggregation — see
docs/architecture/api-guidelines.md's thin-controller rule (the same rule
this module follows, just for server-rendered HTML instead of DRF JSON).
Read-only throughout: nothing here writes to the database.
"""

from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.profile_activation_service import (
    ProfileActivationError,
    ProfileActivationService,
)
from apps.accounts.services.verification_review_service import (
    VerificationReviewError,
    VerificationReviewService,
)
from apps.commission.services.dispute_resolution_service import DisputeResolutionService
from apps.commission.services.errors import CommissionError
from apps.commission.services.queries import FinancialCoreQueryService
from apps.kernel.api.health import HealthCheckView
from apps.reporting.services import (
    FinancialReportService,
    MarketplaceReportService,
    OperationalReportService,
    ProviderReportService,
)

from . import permission_keys
from .forms import DisputeResolveForm, DocumentReviewForm
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


# ============================================================
# Financial Core PR-B — Escrow/objection/dispute/release-refund
# platform visibility (Section 24 minimal admin-portal UI). Read-only
# except dispute_resolve_action, a deliberate, narrowly-scoped exception
# to this module's otherwise read-only convention — the only write action
# Section 24 requires here, gated behind COMMISSION_DISPUTE_RESOLVE.
# ============================================================


@require_GET
def escrow_overview(request):
    """GET /admin-portal/financial/escrows/ — every Escrow for the caller's own tenant."""
    tenant_id = require_admin_permission(request, permission_keys.COMMISSION_ESCROW_VIEW)
    escrows = FinancialCoreQueryService.list_escrows_for_tenant(tenant_id=tenant_id)
    return render(request, "admin_portal/escrow_overview.html", {"escrows": escrows})


@require_GET
def escrow_detail(request, escrow_id):
    """GET /admin-portal/financial/escrows/<escrow_id>/ — movements, disputes, release/refund instructions."""
    tenant_id = require_admin_permission(request, permission_keys.COMMISSION_ESCROW_VIEW)
    detail = FinancialCoreQueryService.get_escrow_detail(tenant_id=tenant_id, escrow_id=escrow_id)
    if detail is None:
        raise Http404("Escrow not found.")
    return render(request, "admin_portal/escrow_detail.html", {"escrow": detail})


@require_GET
def dispute_queue(request):
    """GET /admin-portal/financial/disputes/ — every Dispute for the caller's own tenant."""
    tenant_id = require_admin_permission(request, permission_keys.COMMISSION_ESCROW_VIEW)
    disputes = FinancialCoreQueryService.list_disputes_for_tenant(tenant_id=tenant_id)
    return render(request, "admin_portal/dispute_queue.html", {"disputes": disputes})


@require_GET
def dispute_detail(request, dispute_id):
    """GET /admin-portal/financial/disputes/<dispute_id>/ — dispute detail + resolve form."""
    tenant_id = require_admin_permission(request, permission_keys.COMMISSION_ESCROW_VIEW)
    dispute = FinancialCoreQueryService.get_dispute_detail(tenant_id=tenant_id, dispute_id=dispute_id)
    if dispute is None:
        raise Http404("Dispute not found.")
    return render(
        request,
        "admin_portal/dispute_detail.html",
        {
            "dispute": dispute,
            "resolve_form": DisputeResolveForm(initial={"customer_refund_amount_irr": dispute.disputed_amount_irr}),
        },
    )


@require_http_methods(["POST"])
def dispute_resolve_action(request, dispute_id):
    """POST /admin-portal/financial/disputes/<dispute_id>/resolve/ — the one
    write action this otherwise read-only module needs (Section 14/24):
    allocates the dispute's exact blocked amount into customer refund
    and/or platform/company/caregiver release. DisputeResolutionService
    itself re-validates the COMMISSION_DISPUTE_RESOLVE permission and the
    exact conservation invariant — this view does not duplicate that
    business logic, only the permission gate needed to even show the page."""
    tenant_id = require_admin_permission(request, permission_keys.COMMISSION_DISPUTE_RESOLVE)
    dispute = FinancialCoreQueryService.get_dispute_detail(tenant_id=tenant_id, dispute_id=dispute_id)
    if dispute is None:
        raise Http404("Dispute not found.")

    form = DisputeResolveForm(request.POST)
    if form.is_valid():
        try:
            DisputeResolutionService.resolve(
                dispute_id=dispute.id,
                reason=form.cleaned_data["reason"],
                actor=request.user,
                idempotency_key=f"admin-resolve:{dispute.id}",
                customer_refund_amount_irr=form.cleaned_data["customer_refund_amount_irr"],
                platform_amount_irr=form.cleaned_data["platform_amount_irr"],
                company_amount_irr=form.cleaned_data["company_amount_irr"],
                caregiver_amount_irr=form.cleaned_data["caregiver_amount_irr"],
            )
        except CommissionError:
            pass  # Invalid allocation / already resolved — page still shows current state.
    return redirect("admin_portal:dispute-detail", dispute_id=dispute.id)


@require_GET
def release_refund_overview(request):
    """GET /admin-portal/financial/instructions/ — every ReleaseInstruction/RefundInstruction for the tenant."""
    tenant_id = require_admin_permission(request, permission_keys.COMMISSION_ESCROW_VIEW)
    return render(
        request,
        "admin_portal/release_refund_overview.html",
        {
            "releases": FinancialCoreQueryService.list_release_instructions_for_tenant(tenant_id=tenant_id),
            "refunds": FinancialCoreQueryService.list_refund_instructions_for_tenant(tenant_id=tenant_id),
        },
    )


@require_GET
def feature_gate_overview(request):
    """GET /admin-portal/financial/feature-gates/ — PR-B's 5 feature-gate states for the caller's own tenant."""
    tenant_id = require_admin_permission(request, permission_keys.COMMISSION_ESCROW_VIEW)
    gates = FinancialCoreQueryService.get_feature_gate_status(tenant_id=tenant_id)
    return render(request, "admin_portal/feature_gate_overview.html", {"gates": gates})


@require_GET
def document_verification_queue(request):
    """GET /admin-portal/verification/documents/ — every PENDING VerificationDocument for the caller's own tenant."""
    tenant_id = require_admin_permission(request, permission_keys.DOCUMENT_REVIEW)
    documents = VerificationReviewService.list_pending_for_tenant(tenant_id=tenant_id)
    return render(request, "admin_portal/document_verification_queue.html", {"documents": documents})


@require_GET
def document_verification_detail(request, document_id):
    """GET /admin-portal/verification/documents/<document_id>/ — document detail + review form.

    A document belonging to a different tenant raises AccountsError from
    the service (tenant-scoped lookup), which this view maps to the same
    Http404 a genuinely nonexistent document would raise — cross-tenant
    review attempts cannot distinguish the two."""
    tenant_id = require_admin_permission(request, permission_keys.DOCUMENT_REVIEW)
    try:
        document = VerificationReviewService.get_document_for_tenant(tenant_id=tenant_id, document_id=document_id)
    except AccountsError:
        raise Http404("Document not found.") from None
    return render(
        request,
        "admin_portal/document_verification_detail.html",
        {"document": document, "review_form": DocumentReviewForm()},
    )


@require_GET
def document_verification_file(request, document_id):
    """GET /admin-portal/verification/documents/<document_id>/file/ — streams the
    private uploaded file. Gated by the exact same permission and tenant
    scope as the detail page — this is the sole authenticated path to the
    original file; it is never linked from any public page (see
    `apps.accounts.models.media_paths`'s own docstring on the public/
    private storage split)."""
    tenant_id = require_admin_permission(request, permission_keys.DOCUMENT_REVIEW)
    try:
        document = VerificationReviewService.get_document_for_tenant(tenant_id=tenant_id, document_id=document_id)
    except AccountsError:
        raise Http404("Document not found.") from None
    return FileResponse(document.file.open("rb"), filename=document.file.name.rsplit("/", 1)[-1])


@require_http_methods(["POST"])
def document_verification_review_action(request, document_id):
    """POST /admin-portal/verification/documents/<document_id>/review/ — approve,
    reject, or request correction. VerificationReviewService itself
    re-validates the accounts.document.review permission, tenant scope,
    self-review, and legal-transition rules — this view only resolves
    which service method to call and surfaces a controlled error back onto
    the same detail page rather than raising."""
    tenant_id = require_admin_permission(request, permission_keys.DOCUMENT_REVIEW)
    try:
        document = VerificationReviewService.get_document_for_tenant(tenant_id=tenant_id, document_id=document_id)
    except AccountsError:
        raise Http404("Document not found.") from None

    form = DocumentReviewForm(request.POST)
    if form.is_valid():
        action = form.cleaned_data["action"]
        reason = form.cleaned_data["reason"]
        try:
            if action == DocumentReviewForm.APPROVE:
                VerificationReviewService.approve(document_id=document.id, tenant_id=tenant_id, reviewer=request.user)
            elif action == DocumentReviewForm.REJECT:
                VerificationReviewService.reject(
                    document_id=document.id, tenant_id=tenant_id, reviewer=request.user, reason=reason,
                )
            else:
                VerificationReviewService.request_correction(
                    document_id=document.id, tenant_id=tenant_id, reviewer=request.user, reason=reason,
                )
        except VerificationReviewError:
            pass  # Illegal transition / missing reason — page still shows current state.
    return redirect("admin_portal:document-verification-detail", document_id=document.id)


@require_GET
def caregiver_activation_detail(request, caregiver_id):
    """GET /admin-portal/verification/caregivers/<caregiver_id>/ — eligibility,
    blocking reasons, and the activate action, for a caregiver in the
    caller's own tenant. Cross-tenant/nonexistent caregivers both 404."""
    tenant_id = require_admin_permission(request, permission_keys.PROFILE_ACTIVATE)
    try:
        caregiver = ProfileActivationService.get_caregiver_for_tenant(caregiver_id=caregiver_id, tenant_id=tenant_id)
    except AccountsError:
        raise Http404("Profile not found.") from None

    eligibility = ActivationEligibilityService.evaluate_caregiver(caregiver)
    is_activated = ProfileActivationService.is_activated(
        resource_type="CaregiverProfile", resource_id=caregiver.id, tenant_id=tenant_id,
    )
    return render(
        request,
        "admin_portal/caregiver_activation_detail.html",
        {"caregiver": caregiver, "eligibility": eligibility, "is_activated": is_activated},
    )


@require_http_methods(["POST"])
def caregiver_activate_action(request, caregiver_id):
    """POST /admin-portal/verification/caregivers/<caregiver_id>/activate/ —
    ProfileActivationService itself re-validates permission, tenant scope,
    self-activation, and eligibility; this view only surfaces a refusal
    back onto the same detail page rather than raising."""
    tenant_id = require_admin_permission(request, permission_keys.PROFILE_ACTIVATE)
    try:
        ProfileActivationService.activate_caregiver(caregiver_id, tenant_id=tenant_id, actor=request.user)
    except (ProfileActivationError, AccountsError):
        pass  # Ineligible / not found / self-activation — page still shows current state.
    return redirect("admin_portal:caregiver-activation-detail", caregiver_id=caregiver_id)


@require_GET
def organization_activation_detail(request, organization_id):
    """GET /admin-portal/verification/organizations/<organization_id>/ — same
    shape as the caregiver detail page, for organizations."""
    tenant_id = require_admin_permission(request, permission_keys.PROFILE_ACTIVATE)
    try:
        organization = ProfileActivationService.get_organization_for_tenant(
            organization_id=organization_id, tenant_id=tenant_id,
        )
    except AccountsError:
        raise Http404("Profile not found.") from None

    eligibility = ActivationEligibilityService.evaluate_organization(organization)
    is_activated = ProfileActivationService.is_activated(
        resource_type="OrganizationProfile", resource_id=organization.id, tenant_id=tenant_id,
    )
    return render(
        request,
        "admin_portal/organization_activation_detail.html",
        {"organization": organization, "eligibility": eligibility, "is_activated": is_activated},
    )


@require_http_methods(["POST"])
def organization_activate_action(request, organization_id):
    """POST /admin-portal/verification/organizations/<organization_id>/activate/"""
    tenant_id = require_admin_permission(request, permission_keys.PROFILE_ACTIVATE)
    try:
        ProfileActivationService.activate_organization(organization_id, tenant_id=tenant_id, actor=request.user)
    except (ProfileActivationError, AccountsError):
        pass  # Ineligible / not found / self-activation — page still shows current state.
    return redirect("admin_portal:organization-activation-detail", organization_id=organization_id)
