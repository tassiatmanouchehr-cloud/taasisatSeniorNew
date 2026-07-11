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
from django.shortcuts import render

from .services.directory_service import CAREGIVER_SUPPLIER_TYPES, CaregiverDirectoryService
from .services.home_service import HomePageService
from .services.profile_service import CaregiverPublicProfileService


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
    profile = CaregiverPublicProfileService.get_profile(supplier_id)
    if profile is None:
        raise Http404("Caregiver profile not found.")
    return render(request, "public_site/caregiver_profile.html", {"profile": profile})


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
