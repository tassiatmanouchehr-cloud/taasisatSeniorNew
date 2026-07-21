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

Sprint 2.2 (Caregiver Gallery and Media Portfolio): `_gallery()` reuses
the exact same `is_visible=True` per-item filter `_skills()`/
`_experience()` already established — no second visibility rule. Because
`_gallery()` only ever runs after `common.is_publicly_visible(supplier)`
has already gated the whole method, a caregiver who fails the canonical
policy (DRAFT/suspended/unverified/inactive account/inactive membership)
never has their gallery resolved at all, not merely filtered client-side.

Sprint 2.3 (Credentials, Skills, Experience, Highlights): `_highlights()`
and `_verification_badges()` are pure, read-only aggregations over data
this method already resolved for the rest of the page (`skills`,
`credentials`, `rating`, `completed_jobs`) — neither adds a query, and
neither runs at all unless the same canonical visibility gate above has
already passed, exactly like every other section on this page. Precise
badges only ("Profile verified", "Identity verified", "Professional
credential verified") — never one generic "Verified" badge conflating
unrelated claims. Self-declared experience is never labeled as platform-
verified — that distinction is made explicit in the template, not derived
here (there is no experience-verification record to derive it from).

Sprint 2.4 (Caregiver Availability and Working Schedule): `_schedule_summary()`
adds exactly one bounded query
(`AvailabilityQueryService.get_distinct_active_days()`), run only after the
same canonical visibility gate above has already passed — a
DRAFT/suspended/unverified/inactive-account caregiver's schedule is never
even queried. The summary is deliberately day-labels-only: no exact
start/end time, no blocked-period/time-off entry, and no reason ever
reaches this page — apps.availability.models.AvailabilityBlockedPeriod
rows (and their `reason`/`notes`) are never read here at all. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020 Decision 4.
"""

from apps.accounts.services.favorites import FavoritesService
from apps.accounts.services.public_credential_selector import PublicCredentialSelector
from apps.accounts.services.supplier_bridge import resolve_supplier_entity
from apps.availability.models import PERSIAN_DAY_LABELS
from apps.availability.services.query_service import AvailabilityQueryService
from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus
from apps.kernel.services.tenant_service import TenantService
from apps.orders.services.queries import CatalogQueryService
from apps.reviews.models import Review, ReviewModerationStatus

from . import common
from .directory_service import CAREGIVER_SUPPLIER_TYPES
from .viewmodels import (
    AvailabilityScheduleSummaryViewModel,
    CaregiverProfileViewModel,
    ProfessionalHighlightsViewModel,
    PublicCredentialViewModel,
    PublicExperienceViewModel,
    PublicGalleryItemViewModel,
    PublicSkillViewModel,
    ReviewViewModel,
    VerificationBadgeViewModel,
)

MAX_REVIEWS = 20


class CaregiverPublicProfileService:
    """Read-only: resolves a single supplier_id into a public profile ViewModel."""

    @classmethod
    def get_profile(cls, supplier_id, *, tenant_id=None, customer=None) -> CaregiverProfileViewModel | None:
        """`customer` (Phase 4 Sprint 4.1, optional, defaults to None):
        the authenticated visitor's own CustomerProfile, if any — never
        resolved here, always passed in already-resolved by the view, so
        this service never touches request/session state. When absent
        (anonymous visitor, or an authenticated non-customer actor), the
        returned ViewModel's is_favorited is simply False; no error, no
        second visibility/resolution path."""
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
        gallery = cls._gallery(caregiver)
        completed_jobs = common.completed_jobs_count(tenant_id=tenant_id, supplier_id=supplier.id)

        return CaregiverProfileViewModel(
            supplier_id=supplier.id,
            display_name=supplier.display_name,
            avatar_initial=common.avatar_initial(supplier.display_name),
            avatar_url=attrs["avatar_url"],
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
            completed_jobs=completed_jobs,
            reviews=reviews,
            skills=skills,
            experience=experience,
            credentials=credentials,
            gallery=gallery,
            highlights=cls._highlights(
                years_experience=attrs["years_experience"],
                skills=skills,
                credentials=credentials,
                completed_jobs=completed_jobs,
                review_count=rating.review_count,
            ),
            verification_badges=cls._verification_badges(attrs, credentials),
            schedule_summary=cls._schedule_summary(supplier),
            is_favorited=FavoritesService.is_favorited(customer, supplier_id=supplier.id) if customer else False,
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
                document_type=summary.document_type,
            )
            for summary in summaries
        )

    @classmethod
    def _gallery(cls, caregiver) -> tuple[PublicGalleryItemViewModel, ...]:
        """Sprint 2.2 (Caregiver Gallery and Media Portfolio). Only
        `is_visible=True` items — the same per-item visibility lever
        `_skills()`/`_experience()` already apply. Never reached at all
        unless `get_profile()`'s own `common.is_publicly_visible(supplier)`
        gate above already passed, so a DRAFT/suspended/unverified/
        inactive-account caregiver's gallery is never resolved in the
        first place — no separate profile-level visibility rule is
        duplicated here."""
        if caregiver is None:
            return ()
        visible = caregiver.gallery_items.filter(is_visible=True)
        return tuple(
            PublicGalleryItemViewModel(
                image_url=item.image.url if item.image else "",
                caption=item.caption,
                alt_text=item.alt_text,
            )
            for item in visible
        )

    @staticmethod
    def _highlights(
        *,
        years_experience,
        skills,
        credentials,
        completed_jobs: int,
        review_count: int,
    ) -> ProfessionalHighlightsViewModel:
        return ProfessionalHighlightsViewModel(
            years_experience=years_experience,
            verified_credential_count=len(credentials),
            visible_skill_count=len(skills),
            completed_jobs_count=completed_jobs,
            review_count=review_count,
        )

    @staticmethod
    def _verification_badges(attrs, credentials) -> tuple[VerificationBadgeViewModel, ...]:
        badges = []
        if attrs["verification_status"] == "verified":
            badges.append(VerificationBadgeViewModel(label="نمایه تأییدشده", variant="info"))
        if any(credential.document_type == "identity" for credential in credentials):
            badges.append(VerificationBadgeViewModel(label="هویت تأییدشده", variant="success"))
        if credentials:
            badges.append(VerificationBadgeViewModel(label="مدرک حرفه‌ای تأییدشده", variant="success"))
        return tuple(badges)

    @staticmethod
    def _schedule_summary(supplier) -> AvailabilityScheduleSummaryViewModel:
        """Sprint 2.4. Day labels only — never exact start/end times, never
        a blocked-period/time-off entry or its reason. Only ever called
        after get_profile()'s own common.is_publicly_visible(supplier) gate
        has already passed."""
        days = AvailabilityQueryService.get_distinct_active_days(supplier=supplier)
        return AvailabilityScheduleSummaryViewModel(
            has_schedule=bool(days),
            available_day_labels=tuple(PERSIAN_DAY_LABELS[day] for day in days),
        )

    @classmethod
    def _reviews(cls, supplier, *, tenant_id) -> tuple[ReviewViewModel, ...]:
        approved = Review.objects.filter(
            tenant_id=tenant_id,
            supplier=supplier,
            moderation_status=ReviewModerationStatus.APPROVED,
        ).order_by("-created_at")[:MAX_REVIEWS]
        return common.reviews_to_viewmodels(approved)
