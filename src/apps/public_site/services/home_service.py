"""
HomePageService — Epic 06 (Marketplace Profiles & Discovery).

Builds the Home Page ViewModel entirely from real data: real
ServiceCategory rows, real ranked caregivers (reusing
CaregiverDirectoryService.featured()/available_cities()), and real,
moderator-APPROVED reviews only — never fabricated testimonials. If a
section genuinely has no data yet (e.g. zero approved reviews on a fresh
tenant), it is returned empty and the template renders an honest empty
state instead of inventing content.
"""

from apps.kernel.services.tenant_service import TenantService
from apps.orders.services.queries import CatalogQueryService
from apps.reviews.models import Review, ReviewModerationStatus

from . import common
from .directory_service import CaregiverDirectoryService
from .viewmodels import FilterOptionViewModel, HomePageViewModel, ReviewViewModel, ServiceCategoryViewModel

FEATURED_CAREGIVERS_LIMIT = 4
REVIEWS_LIMIT = 3


class HomePageService:
    """Read-only: assembles everything the Home Page template needs."""

    @classmethod
    def get_home_view(cls, *, tenant_id=None) -> HomePageViewModel:
        tenant_id = tenant_id or TenantService.get_default_tenant_id()

        cities = CaregiverDirectoryService.available_cities(tenant_id=tenant_id)

        return HomePageViewModel(
            service_categories=cls._service_categories(tenant_id),
            featured_caregivers=CaregiverDirectoryService.featured(
                tenant_id=tenant_id, limit=FEATURED_CAREGIVERS_LIMIT
            ),
            reviews=cls._reviews(tenant_id),
            city_options=tuple(FilterOptionViewModel(value=c, label=c) for c in cities),
        )

    # ------------------------------------------------------------------

    @classmethod
    def _service_categories(cls, tenant_id) -> tuple[ServiceCategoryViewModel, ...]:
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).order_by("sort_order", "name")
        return tuple(
            ServiceCategoryViewModel(
                id=category.id,
                name=category.name,
                slug=category.slug,
                icon=category.icon,
                description=category.description,
                directory_url=f"/find-a-caregiver/?service={category.id}",
            )
            for category in categories
        )

    @classmethod
    def _reviews(cls, tenant_id) -> tuple[ReviewViewModel, ...]:
        approved = Review.objects.filter(
            tenant_id=tenant_id,
            moderation_status=ReviewModerationStatus.APPROVED,
        ).order_by("-created_at")[:REVIEWS_LIMIT]
        return common.reviews_to_viewmodels(approved)
