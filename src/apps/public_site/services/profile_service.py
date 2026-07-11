"""
CaregiverPublicProfileService — Epic 06 (Marketplace Profiles & Discovery).

Builds the Public Caregiver Profile page. Only ever returns a profile for
a supplier that is genuinely public-eligible (active ServiceSupplier row,
active CaregiverProfile, and a caregiver-type supplier — never a company/
ORGANIZATION supplier, which has no bio/skills/experience of its own).
Never reads or returns anything document-shaped — only the verification
*status* label, per the Epic's explicit "do not expose private documents"
requirement.
"""

from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus
from apps.kernel.services.tenant_service import TenantService
from apps.orders.services.queries import CatalogQueryService
from apps.reviews.models import Review, ReviewModerationStatus

from . import common
from .directory_service import CAREGIVER_SUPPLIER_TYPES
from .viewmodels import CaregiverProfileViewModel, ReviewViewModel

MAX_REVIEWS = 20


class CaregiverPublicProfileService:
    """Read-only: resolves a single supplier_id into a public profile ViewModel."""

    @classmethod
    def get_profile(cls, supplier_id, *, tenant_id=None) -> CaregiverProfileViewModel | None:
        tenant_id = tenant_id or TenantService.get_default_tenant_id()

        try:
            supplier = ServiceSupplier.objects.get(
                id=supplier_id,
                tenant_id=tenant_id,
                status=SupplierStatus.ACTIVE,
                supplier_type__in=CAREGIVER_SUPPLIER_TYPES,
            )
        except ServiceSupplier.DoesNotExist:
            return None

        if not common.is_publicly_visible(supplier):
            return None

        attrs = common.supplier_entity_attrs(supplier)
        rating = common.rating_summary(supplier)
        service_names = cls._service_names(supplier, tenant_id=tenant_id)
        reviews = cls._reviews(supplier, tenant_id=tenant_id)

        return CaregiverProfileViewModel(
            supplier_id=supplier.id,
            display_name=supplier.display_name,
            avatar_initial=common.avatar_initial(supplier.display_name),
            city=attrs["city"],
            specialty=attrs["specialty"],
            bio=attrs["bio"],
            years_experience=attrs["years_experience"],
            service_radius_km=attrs["service_radius_km"],
            service_names=service_names,
            is_organization_affiliated=common.is_organization_affiliated(supplier),
            availability_status=supplier.availability_status,
            availability_label=common.availability_label(supplier.availability_status),
            avatar_status_dot=common.avatar_status_dot(supplier.availability_status),
            verification_status=attrs["verification_status"],
            verification_label=common.verification_label(attrs["verification_status"]),
            is_verified=attrs["verification_status"] == "verified",
            rating=rating,
            completed_jobs=common.completed_jobs_count(tenant_id=tenant_id, supplier_id=supplier.id),
            reviews=reviews,
        )

    # ------------------------------------------------------------------

    @classmethod
    def _service_names(cls, supplier, *, tenant_id) -> tuple[str, ...]:
        """supplier.service_categories stores ServiceCategory ids as strings."""
        category_ids = supplier.service_categories or []
        if not category_ids:
            return ()
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).filter(id__in=category_ids)
        return tuple(category.name for category in categories.order_by("sort_order", "name"))

    @classmethod
    def _reviews(cls, supplier, *, tenant_id) -> tuple[ReviewViewModel, ...]:
        approved = Review.objects.filter(
            tenant_id=tenant_id,
            supplier=supplier,
            moderation_status=ReviewModerationStatus.APPROVED,
        ).order_by("-created_at")[:MAX_REVIEWS]
        return common.reviews_to_viewmodels(approved)
