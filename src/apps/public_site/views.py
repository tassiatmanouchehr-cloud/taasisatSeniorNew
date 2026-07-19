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

from .services.customer_context import require_customer, resolve_customer_or_none
from .services.directory_service import CAREGIVER_SUPPLIER_TYPES, CaregiverDirectoryService
from .services.home_service import HomePageService
from .services.organization_directory_service import OrganizationDirectoryService
from .services.organization_profile_service import OrganizationPublicProfileService
from .services.profile_service import CaregiverPublicProfileService
from .services.tenant_context import resolve_public_tenant


def home(request):
    tenant_id, tenant_slug = resolve_public_tenant(request)
    home_view = HomePageService.get_home_view(tenant_id=tenant_id, tenant_slug=tenant_slug)
    return render(request, "public_site/home.html", {"home": home_view})


def find_a_caregiver(request):
    tenant_id, tenant_slug = resolve_public_tenant(request)
    supplier_type = request.GET.get("type") or None
    if supplier_type not in CAREGIVER_SUPPLIER_TYPES:
        supplier_type = None

    page_view = CaregiverDirectoryService.search(
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        text=request.GET.get("q", ""),
        city=request.GET.get("city") or None,
        supplier_type=supplier_type,
        service_category_id=request.GET.get("service") or None,
        availability_status=request.GET.get("availability") or None,
        page=request.GET.get("page", 1),
    )
    return render(request, "public_site/caregiver_directory.html", {"page": page_view})


def caregiver_profile(request, supplier_id):
    tenant_id, _tenant_slug = resolve_public_tenant(request)
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
    (no Favorite row created, no distinguishing error) rather than
    disclosed, matching this codebase's established non-disclosure
    convention for ownership-scoped lookups. PR #16 architecture-review
    remediation (second pass): expected_supplier_types pins this route to
    CAREGIVER_SUPPLIER_TYPES only, and — since remove_favorite() never
    raises AccountsError, this except branch is only ever reached from a
    failed add_favorite() — an invalid id now redirects to the caregiver
    directory listing instead of the (possibly nonexistent-for-this-route)
    supplier's own profile URL, so a rejected mutation never lands the
    caller on a 404. A successful mutation still redirects to the
    supplier's own profile page, which is now guaranteed to resolve
    (existence/tenant/type/status were all just proven by add_favorite())."""
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
        return redirect("public_site:find-a-caregiver")
    return redirect("public_site:caregiver-profile", supplier_id=supplier_id)


def find_an_organization(request):
    tenant_id, tenant_slug = resolve_public_tenant(request)
    page_view = OrganizationDirectoryService.search(
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        text=request.GET.get("q", ""),
        city=request.GET.get("city") or None,
        service_category_id=request.GET.get("service") or None,
        page=request.GET.get("page", 1),
    )
    return render(request, "public_site/organization_directory.html", {"page": page_view})


def organization_profile(request, supplier_id):
    tenant_id, _tenant_slug = resolve_public_tenant(request)
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
    contract, see that view's own docstring, including the second-pass
    remediation redirecting a rejected mutation to the organization
    directory listing rather than the (possibly wrong-type) supplier's
    own profile URL."""
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
        return redirect("public_site:organization-directory")
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
