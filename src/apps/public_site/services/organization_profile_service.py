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

Phase 3 Sprint 3.2 (Company Professional Profile and Public Presence)
remediation: get_profile() previously re-implemented its own, weaker
visibility check (`attrs["profile_status"] != "active"` only) instead of
calling the canonical `common.is_publicly_visible_attrs()` — the same
function `apps.public_site.services.profile_service
.CaregiverPublicProfileService.get_profile()` already uses, and the one
`is_publicly_visible_attrs()`'s own module docstring already claims every
public entry point uses ("there is exactly one implementation of "is
this publicly visible""). That was untrue for this function: an
ACTIVE-but-UNVERIFIED organization, or one whose admin account had been
deactivated, was still publicly visible. Fixed to call the same
canonical function, closing that gap — no second visibility policy.

PR #13 architecture-review remediation: the public profile is now the
one place a caregiver-portfolio-style "professional profile" capability
(this sprint's own stated purpose) omitted the organization's own
already-uploaded logo, leaving it disconnected from the public presence
it is meant to represent. Added `logo_url` — the existing
`OrganizationProfile.logo` field's own `.url` (Django's standard
storage-URL abstraction, never a filesystem path), exposed only when a
file is actually present. No new field, no new upload path, no second
media pipeline — this reads the exact same `logo` field
`apps.organization_portal.services.profile_service
.OrganizationProfilePresentationService.get_profile_view()` already
exposes to the owning admin, just gated behind the same
`is_publicly_visible_attrs()` check every other field on this ViewModel
already goes through."""

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
        if not common.is_publicly_visible_attrs(attrs):
            return None

        entity = resolve_supplier_entity(supplier)
        active_provider_count = OrganizationStaffService.list_active_caregivers(entity).count() if entity else 0
        rating = common.rating_summary(supplier)

        return OrganizationProfileViewModel(
            supplier_id=supplier.id,
            name=supplier.display_name,
            logo_initial=common.avatar_initial(supplier.display_name),
            logo_url=entity.logo.url if entity and entity.logo else "",
            headline=attrs["headline"],
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
