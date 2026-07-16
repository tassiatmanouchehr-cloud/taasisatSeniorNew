"""
CustomerFavoritesPresentationService — Phase 4 Sprint 4.1 (Customer
Favorites and Saved Providers).

Assembles the "My Favorites" page ViewModel from `FavoritesService
.list_favorites_for_customer()`'s output. Reuses the exact bulk-resolution
building blocks both public directories already established — never a
per-row supplier/rating/visibility/media query:

- `CaregiverDirectoryService.build_cards_for_supplier_ids()` /
  `OrganizationDirectoryService.build_cards_for_supplier_ids()` (Sprint
  4.1 additions to those existing services) resolve every visible
  favorited supplier's card in a small, fixed number of queries per
  supplier-type bucket, regardless of how many favorites are on the page.
- `apps.public_site.services.common.parse_page()`/`build_pagination()`
  (Sprint 3.3) — the same shared pagination helpers both directory
  services already use, PAGE_SIZE=12 to match their own convention.

Decision C/D (Sprint 4.1 ADR): no shared/canonical discovery-card
projection was introduced — `CaregiverCardViewModel`/
`OrganizationCardViewModel` remain deliberately distinct (ADM-025). This
service composes a lightweight `FavoriteRowViewModel` wrapper around
whichever one already applies per row, discriminated by
`supplier.supplier_type`.
"""

import math

from apps.kernel.models.supplier import SupplierType
from apps.public_site.services import common
from apps.public_site.services.directory_service import CAREGIVER_SUPPLIER_TYPES, CaregiverDirectoryService
from apps.public_site.services.organization_directory_service import OrganizationDirectoryService

from .viewmodels import FavoriteRowViewModel, FavoritesListViewModel

PAGE_SIZE = 12


class CustomerFavoritesPresentationService:
    """Read-only: assembles the customer's own favorites list page."""

    @classmethod
    def build_list_view(cls, *, favorites, tenant_id, page=1) -> FavoritesListViewModel:
        favorites = list(favorites)

        total_count = len(favorites)
        total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
        current_page = max(1, min(common.parse_page(page), total_pages))
        offset = (current_page - 1) * PAGE_SIZE
        page_favorites = favorites[offset : offset + PAGE_SIZE]

        caregiver_ids = [
            favorite.supplier_id for favorite in page_favorites
            if favorite.supplier.supplier_type in CAREGIVER_SUPPLIER_TYPES
        ]
        organization_ids = [
            favorite.supplier_id for favorite in page_favorites
            if favorite.supplier.supplier_type == SupplierType.ORGANIZATION
        ]

        caregiver_cards = CaregiverDirectoryService.build_cards_for_supplier_ids(caregiver_ids, tenant_id=tenant_id)
        organization_cards = OrganizationDirectoryService.build_cards_for_supplier_ids(
            organization_ids, tenant_id=tenant_id,
        )

        rows = tuple(cls._build_row(favorite, caregiver_cards, organization_cards) for favorite in page_favorites)

        pagination = common.build_pagination(
            current_page=current_page,
            total_pages=total_pages,
            total_count=total_count,
            base_url="/portal/favorites/",
            params={},
        )

        return FavoritesListViewModel(rows=rows, pagination=pagination)

    @staticmethod
    def _build_row(favorite, caregiver_cards, organization_cards) -> FavoriteRowViewModel:
        is_caregiver = favorite.supplier.supplier_type in CAREGIVER_SUPPLIER_TYPES
        supplier_type_label = "caregiver" if is_caregiver else "organization"
        caregiver_card = caregiver_cards.get(favorite.supplier_id) if is_caregiver else None
        organization_card = organization_cards.get(favorite.supplier_id) if not is_caregiver else None

        return FavoriteRowViewModel(
            favorite_id=str(favorite.id),
            supplier_id=str(favorite.supplier_id),
            supplier_type=supplier_type_label,
            saved_at_label=favorite.created_at.strftime("%Y/%m/%d"),
            remove_url=f"/portal/favorites/{favorite.supplier_id}/remove/",
            is_currently_public=bool(caregiver_card or organization_card),
            caregiver_card=caregiver_card,
            organization_card=organization_card,
        )
