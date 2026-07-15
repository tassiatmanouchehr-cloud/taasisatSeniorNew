"""
CaregiverPublicProfileService — Epic 06 (Marketplace Profiles & Discovery),
extended in Phase 2.1 (Caregiver Professional Profile Foundation).

Builds the Public Caregiver Profile page. Only ever returns a profile for
a supplier that is genuinely public-eligible (active ServiceSupplier row,
active CaregiverProfile, and a caregiver-type supplier — never a company/
ORGANIZATION supplier, which has no bio/skills/experience of its own).
Never reads or returns anything document-shaped — only the verification
*status* label, per the Epic's explicit "do not expose private documents"
requirement.

BG-022 (2026-07-15): `common.is_publicly_visible()` is now the single
canonical public-visibility policy for every public entry point —
directory, home-page listings, and this detail page all resolve through
it. It requires profile status ACTIVE, verification_status VERIFIED, the
owning account's `is_active`, and organization-membership activity. This
page no longer duplicates any of that locally; see
`apps.public_site.services.common`'s own docstring for the full rule and
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017's remediation note for
why it was originally added only here before being unified.
"""

from apps.accounts.services.public_credential_selector import PublicCredentialSelector
from apps.accounts.services.supplier_bridge import resolve_supplier_entity
from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus
from apps.kernel.services.tenant_service import TenantService
from apps.orders.services.queries import CatalogQueryService
from apps.reviews.models import Review, ReviewModerationStatus

from . import common
from .directory_service import CAREGIVER_SUPPLIER_TYPES
from .viewmodels import (
    CaregiverProfileViewModel,
    PublicCredentialViewModel,
    PublicExperienceViewModel,
    PublicSkillViewModel,
    ReviewViewModel,
)

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
        caregiver = resolve_supplier_entity(supplier)

        rating = common.rating_summary(supplier)
        service_names = cls._service_names(supplier, tenant_id=tenant_id)
        reviews = cls._reviews(supplier, tenant_id=tenant_id)
        skills = cls._skills(caregiver)
        experience = cls._experience(caregiver)
        credentials = cls._credentials(caregiver)

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
            skills=skills,
            experience=experience,
            credentials=credentials,
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
    def _skills(cls, caregiver) -> tuple[PublicSkillViewModel, ...]:
        if caregiver is None:
            return ()
        visible = caregiver.skills.filter(is_visible=True)
        return tuple(PublicSkillViewModel(name=skill.name) for skill in visible)

    @classmethod
    def _experience(cls, caregiver) -> tuple[PublicExperienceViewModel, ...]:
        if caregiver is None:
            return ()
        visible = caregiver.experiences.filter(is_visible=True)
        return tuple(
            PublicExperienceViewModel(
                title=entry.title,
                organization_name=entry.organization_name,
                description=entry.description,
                period_label=cls._period_label(entry),
            )
            for entry in visible
        )

    @staticmethod
    def _period_label(entry) -> str:
        start = entry.start_date.strftime("%Y/%m")
        end = "اکنون" if entry.is_current or not entry.end_date else entry.end_date.strftime("%Y/%m")
        return f"{start} - {end}"

    @classmethod
    def _credentials(cls, caregiver) -> tuple[PublicCredentialViewModel, ...]:
        if caregiver is None:
            return ()
        summaries = PublicCredentialSelector.for_caregiver(caregiver)
        return tuple(
            PublicCredentialViewModel(
                label=summary.label,
                expiry_label=summary.expiry_date.strftime("%Y/%m/%d") if summary.expiry_date else "",
            )
            for summary in summaries
        )

    @classmethod
    def _reviews(cls, supplier, *, tenant_id) -> tuple[ReviewViewModel, ...]:
        approved = Review.objects.filter(
            tenant_id=tenant_id,
            supplier=supplier,
            moderation_status=ReviewModerationStatus.APPROVED,
        ).order_by("-created_at")[:MAX_REVIEWS]
        return common.reviews_to_viewmodels(approved)
