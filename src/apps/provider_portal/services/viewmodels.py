"""
Provider portal ViewModels — Epic 06 Sprint 2 (Shared Portal UI Core,
Provider Profile, Organization Profile).

Frozen dataclasses only. Templates in templates/provider_portal/ consume
exactly these — never a CaregiverProfile/ServiceSupplier instance, never
a raw queryset. Mirrors apps.public_site.services.viewmodels's own
established convention for this Epic.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NavItemViewModel:
    label: str
    url: str
    is_active: bool = False


@dataclass(frozen=True)
class RatingSummaryViewModel:
    average: object  # Decimal | None
    review_count: int
    stars_rounded: int


@dataclass(frozen=True)
class DocumentRowViewModel:
    id: str
    label: str
    status: str
    expiry_label: str
    action_message: str
    replace_url: str


@dataclass(frozen=True)
class BadgeViewModel:
    label: str
    variant: str


@dataclass(frozen=True)
class SummaryItemViewModel:
    label: str
    value: str


@dataclass(frozen=True)
class ProviderProfileViewModel:
    supplier_id: str
    display_name: str
    avatar_url: str
    cover_url: str
    avatar_status_dot: str
    city: str
    specialty: str
    bio: str
    years_experience: int | None
    service_radius_km: int | None
    is_organization_affiliated: bool
    organization_name: str
    availability_label: str
    verification_status: str
    is_verified: bool
    rating: RatingSummaryViewModel
    completed_jobs: int
    service_names: tuple[str, ...]
    badges: tuple[BadgeViewModel, ...] = field(default_factory=tuple)
    documents: tuple[DocumentRowViewModel, ...] = field(default_factory=tuple)
    summary_items: tuple[SummaryItemViewModel, ...] = field(default_factory=tuple)
    completion_percent: int = 0
    completion_missing_labels: tuple[str, ...] = field(default_factory=tuple)
    public_preview_url: str = ""
    is_activated: bool = False
    activation_eligible: bool = False
    activation_blocking_reasons: tuple[str, ...] = field(default_factory=tuple)
    activation_profile_status: str = ""
    """Raw `ProfileStatus` value (draft/active/suspended/archived) — Phase
    1.3 remediation, so the template can display DRAFT/ACTIVE/SUSPENDED
    accurately instead of only a derived eligible/ineligible badge."""
    skills_count: int = 0
    experience_count: int = 0
    public_credential_labels: tuple[str, ...] = field(default_factory=tuple)
    """Which verified credential types will appear on the public profile
    right now — Phase 2.1 Part J ("see which verified credential types
    will appear publicly")."""
    gallery_count: int = 0
    gallery_limit: int = 0


@dataclass(frozen=True)
class SkillRowViewModel:
    id: str
    name: str


@dataclass(frozen=True)
class ExperienceRowViewModel:
    id: str
    title: str
    organization_name: str
    description: str
    start_date: object  # date
    end_date: object  # date | None
    is_current: bool
    period_label: str


@dataclass(frozen=True)
class GalleryItemViewModel:
    id: str
    image_url: str
    caption: str
    alt_text: str
    is_visible: bool


@dataclass(frozen=True)
class ServiceCategoryOptionViewModel:
    value: str
    label: str
    selected: bool = False


@dataclass(frozen=True)
class ProviderBasicInfoFormViewModel:
    display_name: str
    city: str


@dataclass(frozen=True)
class ProviderProfessionalInfoFormViewModel:
    bio: str
    specialty: str
    years_experience: int | None
    service_radius_km: int | None
    service_category_options: tuple[ServiceCategoryOptionViewModel, ...]
