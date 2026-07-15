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


@dataclass(frozen=True)
class OrganizationProfileViewModel:
    """The public Organization Profile page (Epic 06 Sprint 2). Never
    exposes staff details, internal membership notes, financial
    identifiers, internal documents, or platform-admin comments — only
    what the organization itself has designated as public-facing."""

    supplier_id: UUID
    name: str
    logo_initial: str
    city: str
    description: str
    service_names: tuple[str, ...]
    verification_status: str
    verification_label: str
    is_verified: bool
    rating: RatingSummaryViewModel
    active_provider_count: int
