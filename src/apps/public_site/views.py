"""Public marketing website views.

These pages are server-rendered, Persian-first, RTL, and contain no business logic.
They only consume the Enterprise UI Foundation and public templates.

Epic 06 (Marketplace Profiles & Discovery) added the Caregiver Directory
and Public Caregiver Profile pages. Like every other view in this file,
they call exactly one service and render a template — no ORM access here
at all (see apps.kernel.tests.test_architecture_guardrails
.PublicSiteOrmDisciplineTest), matching the thin-controller rule already
enforced for apps.portal/apps.provider_portal/apps.organization_portal.
"""

from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.services.errors import AccountsError
from apps.accounts.services.favorites import FavoritesService
from apps.kernel.models.supplier import SupplierType
from apps.kernel.services.tenant_service import TenantService

from .services.customer_context import require_customer, resolve_customer_or_none
from .services.directory_service import CAREGIVER_SUPPLIER_TYPES, CaregiverDirectoryService
from .services.home_service import HomePageService
from .services.organization_directory_service import OrganizationDirectoryService
from .services.organization_profile_service import OrganizationPublicProfileService
from .services.profile_service import CaregiverPublicProfileService


def _resolve_optional_tenant_hint(request):
    """Public profile pages resolve the platform's single default tenant
    by default (unchanged behavior — returns None, and the profile
    service falls back to TenantService.get_default_tenant_id() exactly
    as before). An explicit ?tenant=<slug> hint lets a caller target a
    different, specific, already-known tenant (e.g. the
    seed_product_walkthrough command's own dedicated demo tenant)
    without ever searching across tenants: the profile lookup stays
    scoped to exactly one resolved tenant_id either way.

    Raises Http404 immediately for an unknown/invalid slug — it is never
    silently substituted with the default, which would blur "no hint
    given" with "wrong hint given"."""
    slug = request.GET.get("tenant")
    if not slug:
        return None
    tenant = TenantService.get_tenant_by_slug(slug)
    if tenant is None:
        raise Http404("Unknown tenant.")
    return tenant.id


def home(request):
    return render(request, "public_site/home.html", {"home": HomePageService.get_home_view()})


def find_a_caregiver(request):
    supplier_type = request.GET.get("type") or None
    if supplier_type not in CAREGIVER_SUPPLIER_TYPES:
        supplier_type = None

    page_view = CaregiverDirectoryService.search(
        text=request.GET.get("q", ""),
        city=request.GET.get("city") or None,
        supplier_type=supplier_type,
        service_category_id=request.GET.get("service") or None,
        availability_status=request.GET.get("availability") or None,
        page=request.GET.get("page", 1),
    )
    return render(request, "public_site/caregiver_directory.html", {"page": page_view})


def caregiver_profile(request, supplier_id):
    tenant_id = _resolve_optional_tenant_hint(request)
    customer = resolve_customer_or_none(request)
    profile = CaregiverPublicProfileService.get_profile(supplier_id, tenant_id=tenant_id, customer=customer)
    if profile is None:
        raise Http404("Caregiver profile not found.")
    return render(
        request, "public_site/caregiver_profile.html", {"profile": profile, "can_favorite": customer is not None},
    )


@require_POST
def caregiver_favorite_toggle(request, supplier_id):
    """Phase 4 Sprint 4.1 (Customer Favorites): toggles the caller's own
    favorite state for this supplier, then redirects back to the same
    profile page — never a client-supplied "next" URL. 403 for anonymous/
    non-customer callers (require_customer()'s own convention, matching
    apps.portal.permissions.require_authenticated() exactly). A
    wrong-tenant/unknown/wrong-type supplier_id is absorbed silently
    (redirect back unchanged) rather than disclosed, matching this
    codebase's established non-disclosure convention for ownership-scoped
    lookups. PR #16 architecture-review remediation: expected_supplier_types
    pins this route to CAREGIVER_SUPPLIER_TYPES only — a supplier UUID of
    the wrong type (e.g. an organization) is rejected exactly like a
    wrong-tenant/unknown one, never creating a Favorite row."""
    customer, tenant_id = require_customer(request)
    action = request.POST.get("action")
    try:
        if action == "remove":
            FavoritesService.remove_favorite(customer, supplier_id=supplier_id)
        else:
            FavoritesService.add_favorite(
                customer, supplier_id=supplier_id, tenant_id=tenant_id,
                expected_supplier_types=CAREGIVER_SUPPLIER_TYPES,
            )
    except AccountsError:
        pass
    return redirect("public_site:caregiver-profile", supplier_id=supplier_id)


def find_an_organization(request):
    page_view = OrganizationDirectoryService.search(
        text=request.GET.get("q", ""),
        city=request.GET.get("city") or None,
        service_category_id=request.GET.get("service") or None,
        page=request.GET.get("page", 1),
    )
    return render(request, "public_site/organization_directory.html", {"page": page_view})


def organization_profile(request, supplier_id):
    tenant_id = _resolve_optional_tenant_hint(request)
    customer = resolve_customer_or_none(request)
    profile = OrganizationPublicProfileService.get_profile(supplier_id, tenant_id=tenant_id, customer=customer)
    if profile is None:
        raise Http404("Organization profile not found.")
    return render(
        request, "public_site/organization_profile.html", {"profile": profile, "can_favorite": customer is not None},
    )


@require_POST
def organization_favorite_toggle(request, supplier_id):
    """Organization-side sibling of caregiver_favorite_toggle() — identical
    contract, see that view's own docstring. Pinned to
    SupplierType.ORGANIZATION only (PR #16 architecture-review
    remediation) — a caregiver supplier UUID is rejected exactly like a
    wrong-tenant/unknown one."""
    customer, tenant_id = require_customer(request)
    action = request.POST.get("action")
    try:
        if action == "remove":
            FavoritesService.remove_favorite(customer, supplier_id=supplier_id)
        else:
            FavoritesService.add_favorite(
                customer, supplier_id=supplier_id, tenant_id=tenant_id,
                expected_supplier_types=(SupplierType.ORGANIZATION,),
            )
    except AccountsError:
        pass
    return redirect("public_site:organization-profile", supplier_id=supplier_id)


def about(request):
    return render(request, "public_site/about.html")


def services(request):
    return render(request, "public_site/services.html")


def how_it_works(request):
    return render(request, "public_site/how_it_works.html")


def contact(request):
    return render(request, "public_site/contact.html")


def pricing(request):
    return render(request, "public_site/pricing.html")


def trust_safety(request):
    return render(request, "public_site/trust_safety.html")


def caregivers(request):
    return render(request, "public_site/caregivers.html")


def organizations(request):
    return render(request, "public_site/organizations.html")


def faq(request):
    return render(request, "public_site/faq.html")


def privacy(request):
    return render(request, "public_site/privacy.html")


def terms(request):
    return render(request, "public_site/terms.html")


def accessibility(request):
    return render(request, "public_site/accessibility.html")


def support(request):
    return render(request, "public_site/support.html")


def service_areas(request):
    return render(request, "public_site/service_areas.html")
