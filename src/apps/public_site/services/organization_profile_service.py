"""
OrganizationPublicProfileService — Epic 06 Sprint 2 (Shared Portal UI
Core, Provider Profile, Organization Profile).

Builds the Public Organization Profile page — the minimal public
organization-profile surface this Sprint's Part F calls for, so
apps.organization_portal's profile-editing experience has a real preview
to link to. Mirrors apps.public_site.services.profile_service
.CaregiverPublicProfileService's own shape and trust boundary exactly:
resolves by supplier_id (not organization_id, exactly like the Caregiver
Profile page resolves by supplier_id, not caregiver_id), never returns a
hidden/inactive organization, never exposes staff details, internal
documents, or anything not already public-safe.

Deliberately duck-types the resolved OrganizationProfile entity via
apps.accounts.services.supplier_bridge.resolve_supplier_entity() instead
of importing OrganizationProfile directly — same guardrail
(ServiceSupplierProfileCouplingTest) and same established pattern as
common.py's own module docstring describes.

Deliberately not the full organization directory (Part F explicitly
scopes this Sprint to "the minimal public organization profile required
to preview real organization data," not a directory) — there is no
"list all organizations" view or route here, only single-organization
lookup by supplier_id.
"""

from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.accounts.services.supplier_bridge import resolve_supplier_entity
from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.services.tenant_service import TenantService
from apps.orders.services.queries import CatalogQueryService

from . import common
from .viewmodels import OrganizationProfileViewModel

VERIFICATION_LABELS = {
    "unverified": "تأییدنشده",
    "pending": "در حال بررسی",
    "verified": "تأییدشده",
    "rejected": "رد شده",
}


class OrganizationPublicProfileService:
    """Read-only: resolves a single supplier_id (SupplierType.ORGANIZATION)
    into a public organization profile ViewModel."""

    @classmethod
    def get_profile(cls, supplier_id, *, tenant_id=None) -> OrganizationProfileViewModel | None:
        tenant_id = tenant_id or TenantService.get_default_tenant_id()

        try:
            supplier = ServiceSupplier.objects.get(
                id=supplier_id,
                tenant_id=tenant_id,
                status=SupplierStatus.ACTIVE,
                supplier_type=SupplierType.ORGANIZATION,
            )
        except ServiceSupplier.DoesNotExist:
            return None

        attrs = common.supplier_entity_attrs(supplier)
        if attrs["profile_status"] != "active":
            return None

        entity = resolve_supplier_entity(supplier)
        active_provider_count = OrganizationStaffService.list_active_caregivers(entity).count() if entity else 0
        rating = common.rating_summary(supplier)

        return OrganizationProfileViewModel(
            supplier_id=supplier.id,
            name=supplier.display_name,
            logo_initial=common.avatar_initial(supplier.display_name),
            city=attrs["city"],
            description=attrs["description"],
            service_names=cls._service_names(supplier, tenant_id=tenant_id),
            verification_status=attrs["verification_status"],
            verification_label=VERIFICATION_LABELS.get(attrs["verification_status"], attrs["verification_status"]),
            is_verified=attrs["verification_status"] == "verified",
            rating=rating,
            active_provider_count=active_provider_count,
        )

    @staticmethod
    def _service_names(supplier, *, tenant_id) -> tuple[str, ...]:
        category_ids = supplier.service_categories or []
        if not category_ids:
            return ()
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).filter(id__in=category_ids)
        return tuple(category.name for category in categories.order_by("sort_order", "name"))
