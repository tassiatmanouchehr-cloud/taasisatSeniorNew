"""
Frozen dataclass ViewModels for the public marketing/discovery pages
(Epic 06 — Marketplace Profiles & Discovery).

Mirrors this codebase's existing internal-DTO convention (see
apps.discovery.services.dto.SearchResultItem, apps.matching.services
.eligibility.EligibilityResult). Templates consume only these — never a
model instance, never a raw queryset — so the presentation layer stays
completely decoupled from the domain models and safe to re-theme.

None of these expose anything a real caregiver/organization would
consider private: no documents, no raw verification-document metadata,
no contact details beyond what the platform already treats as public
(display name, city, bio). Verification is surfaced only as a status
label, never as underlying evidence.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class RatingSummaryViewModel:
    """A supplier's public reputation summary. average is None when the
    supplier has zero approved reviews — templates must render an
    honest "no ratings yet" state rather than a fabricated score."""

    average: Decimal | None
    review_count: int
    stars_rounded: int  # 0-5, nearest whole star, for simple star rendering


@dataclass(frozen=True)
class ReviewViewModel:
    reviewer_name: str
    rating: Decimal
    rating_stars_rounded: int
    written_text: str
    created_at_display: str


@dataclass(frozen=True)
class CaregiverCardViewModel:
    """One row in the Caregiver Directory grid or the Home Page's
    "featured caregivers" section."""

    supplier_id: UUID
    display_name: str
    avatar_initial: str
    city: str
    specialty: str
    bio_snippet: str
    is_organization_affiliated: bool
    availability_status: str
    availability_label: str
    avatar_status_dot: str
    verification_status: str
    verification_label: str
    is_verified: bool
    rating: RatingSummaryViewModel
    completed_jobs: int
    profile_url: str


@dataclass(frozen=True)
class PublicSkillViewModel:
    name: str


@dataclass(frozen=True)
class PublicExperienceViewModel:
    title: str
    organization_name: str
    description: str
    period_label: str


@dataclass(frozen=True)
class PublicCredentialViewModel:
    label: str
    expiry_label: str
    document_type: str = ""
    """The credential type code (e.g. "identity") — Sprint 2.3, needed so
    the presentation layer can derive precise per-type verification
    badges ("Identity verified") without re-deriving them from a raw
    VerificationDocument. A type code, not evidence — safe to expose."""


@dataclass(frozen=True)
class PublicGalleryItemViewModel:
    image_url: str
    caption: str
    alt_text: str


@dataclass(frozen=True)
class ProfessionalHighlightsViewModel:
    """Sprint 2.3 (Credentials, Skills, Experience, Highlights) — small,
    entirely derived read-only summary. Every field is computed from data
    CaregiverPublicProfileService.get_profile() already resolved for the
    rest of the page (skills, experience, credentials, rating,
    completed-jobs count) — nothing here triggers a new query, and
    nothing here is a stored/duplicated statistic."""

    years_experience: int | None
    verified_credential_count: int
    visible_skill_count: int
    completed_jobs_count: int
    review_count: int


@dataclass(frozen=True)
class VerificationBadgeViewModel:
    """One precise verification claim — Sprint 2.3. Deliberately never a
    single generic "Verified" badge: each instance names exactly what was
    verified ("Profile verified", "Identity verified", "Professional
    credential verified"), never implying broader approval than the
    underlying evidence supports."""

    label: str
    variant: str


@dataclass(frozen=True)
class AvailabilityScheduleSummaryViewModel:
    """Sprint 2.4 (Caregiver Availability and Working Schedule) — the safe,
    summarized public presentation of a caregiver's weekly schedule. Named
    distinctly from this module's own `availability_status`/
    `availability_label` fields (real-time online/busy/offline presence,
    unrelated and pre-existing) to avoid confusing the two concepts.
    Deliberately carries day labels only, never exact start/end times, and
    never anything about time-off/blocked periods — see
    CaregiverPublicProfileService._schedule_summary()'s own docstring for
    the privacy reasoning."""

    has_schedule: bool
    available_day_labels: tuple[str, ...]


@dataclass(frozen=True)
class CaregiverProfileViewModel:
    """The full Public Caregiver Profile page."""

    supplier_id: UUID
    display_name: str
    avatar_initial: str
    city: str
    specialty: str
    bio: str
    years_experience: int | None
    service_radius_km: int | None
    service_names: tuple[str, ...]
    is_organization_affiliated: bool
    availability_status: str
    availability_label: str
    avatar_status_dot: str
    verification_status: str
    verification_label: str
    is_verified: bool
    rating: RatingSummaryViewModel
    completed_jobs: int
    reviews: tuple[ReviewViewModel, ...]
    skills: tuple[PublicSkillViewModel, ...] = field(default_factory=tuple)
    experience: tuple[PublicExperienceViewModel, ...] = field(default_factory=tuple)
    credentials: tuple[PublicCredentialViewModel, ...] = field(default_factory=tuple)
    gallery: tuple[PublicGalleryItemViewModel, ...] = field(default_factory=tuple)
    highlights: ProfessionalHighlightsViewModel | None = None
    verification_badges: tuple[VerificationBadgeViewModel, ...] = field(default_factory=tuple)
    schedule_summary: AvailabilityScheduleSummaryViewModel | None = None
    is_favorited: bool = False
    """Phase 4 Sprint 4.1 (Customer Favorites): True only when the
    currently authenticated visitor is a customer and has favorited this
    supplier — False for anonymous visitors and non-customer actors alike
    (get_profile()'s own `customer=None` default), never raising."""


@dataclass(frozen=True)
class ServiceCategoryViewModel:
    id: UUID
    name: str
    slug: str
    icon: str
    description: str
    directory_url: str


@dataclass(frozen=True)
class FilterOptionViewModel:
    value: str
    label: str
    selected: bool = False


@dataclass(frozen=True)
class DirectoryFiltersViewModel:
    city_options: tuple[FilterOptionViewModel, ...]
    service_options: tuple[FilterOptionViewModel, ...]
    type_options: tuple[FilterOptionViewModel, ...]
    availability_options: tuple[FilterOptionViewModel, ...]
    search_text: str = ""
    # Gender is part of the Epic's requested filter set, but no gender
    # field exists anywhere in the backend domain (CaregiverProfile has
    # no such field) — surfaced honestly to the template/report rather
    # than fabricated. See the PR description's "Known limitations".
    gender_filter_supported: bool = False
    # Follow-up to FR-015 (tenant-context propagation in directory-
    # generated navigation): the active tenant hint, if any, so the
    # filter form can resubmit it as a hidden field and the "clear
    # filters" link can preserve it. Empty string on the default-tenant
    # path — never used for query filtering, only for building the two
    # URLs below.
    tenant_slug: str = ""
    reset_url: str = "/find-a-caregiver/"


@dataclass(frozen=True)
class PaginationLinkViewModel:
    number: int
    url: str
    is_current: bool


@dataclass(frozen=True)
class PaginationViewModel:
    current_page: int
    total_pages: int
    total_count: int
    previous_url: str | None
    next_url: str | None
    page_links: tuple[PaginationLinkViewModel, ...]


@dataclass(frozen=True)
class DirectoryPageViewModel:
    caregivers: tuple[CaregiverCardViewModel, ...]
    filters: DirectoryFiltersViewModel
    pagination: PaginationViewModel


@dataclass(frozen=True)
class HomePageViewModel:
    service_categories: tuple[ServiceCategoryViewModel, ...] = field(default_factory=tuple)
    featured_caregivers: tuple[CaregiverCardViewModel, ...] = field(default_factory=tuple)
    reviews: tuple[ReviewViewModel, ...] = field(default_factory=tuple)
    city_options: tuple[FilterOptionViewModel, ...] = field(default_factory=tuple)
    # Follow-up to FR-016 — the resolved public-site tenant's own slug
    # (see apps.public_site.services.tenant_context.resolve_public_tenant()),
    # so the homepage's own search form and "view all caregivers" link
    # can carry it forward. Empty string on the ordinary default-tenant
    # path, matching every directory's own tenant_slug field.
    tenant_slug: str = ""
    caregiver_directory_url: str = "/find-a-caregiver/"


@dataclass(frozen=True)
class OrganizationProfileViewModel:
    """The public Organization Profile page (Epic 06 Sprint 2). Never
    exposes staff details, internal membership notes, financial
    identifiers, internal documents, or platform-admin comments — only
    what the organization itself has designated as public-facing."""

    supplier_id: UUID
    name: str
    logo_initial: str
    logo_url: str
    headline: str
    city: str
    description: str
    service_names: tuple[str, ...]
    verification_status: str
    verification_label: str
    is_verified: bool
    rating: RatingSummaryViewModel
    active_provider_count: int
    is_favorited: bool = False
    """Phase 4 Sprint 4.1 (Customer Favorites) — see
    CaregiverProfileViewModel.is_favorited's own docstring; identical
    contract for the organization public profile page."""


@dataclass(frozen=True)
class OrganizationCardViewModel:
    """One row in the Company Public Directory grid (Sprint 3.3) — the
    organization-side sibling of CaregiverCardViewModel, deliberately
    without any caregiver-only field (specialty, bio, availability)."""

    supplier_id: UUID
    name: str
    logo_initial: str
    logo_url: str
    headline: str
    city: str
    service_names: tuple[str, ...]
    verification_status: str
    verification_label: str
    is_verified: bool
    rating: RatingSummaryViewModel
    active_provider_count: int
    profile_url: str


@dataclass(frozen=True)
class OrganizationDirectoryFiltersViewModel:
    """Sprint 3.3 — leaner than DirectoryFiltersViewModel: only city and
    service-category filters apply to organizations (no type/availability/
    gender, which are caregiver-only concepts)."""

    city_options: tuple[FilterOptionViewModel, ...]
    service_options: tuple[FilterOptionViewModel, ...]
    search_text: str = ""
    # Follow-up to FR-015 — see DirectoryFiltersViewModel's own field of
    # the same name for the full rationale.
    tenant_slug: str = ""
    reset_url: str = "/find-an-organization/"


@dataclass(frozen=True)
class OrganizationDirectoryPageViewModel:
    organizations: tuple[OrganizationCardViewModel, ...]
    filters: OrganizationDirectoryFiltersViewModel
    pagination: PaginationViewModel
