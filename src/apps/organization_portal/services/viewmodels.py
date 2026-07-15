"""
Organization portal ViewModels — Epic 06 Sprint 2 (Shared Portal UI Core,
Provider Profile, Organization Profile).

Frozen dataclasses only. Deliberately not shared with
apps.provider_portal.services.viewmodels — same shape by convention
(mirrors the shared semantic components), never the same class, per this
Sprint's explicit "shared visual structure does not mean shared business
ownership."
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NavItemViewModel:
    label: str
    url: str
    is_active: bool = False


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
class RatingSummaryViewModel:
    average: object
    review_count: int


@dataclass(frozen=True)
class OrganizationProfileViewModel:
    organization_id: str
    name: str
    logo_url: str
    cover_url: str
    city: str
    description: str
    phone: str
    address: str
    verification_status: str
    is_verified: bool
    active_provider_count: int
    rating: RatingSummaryViewModel
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


@dataclass(frozen=True)
class OrganizationProfileFormViewModel:
    name: str
    description: str
    city: str
    phone: str
    address: str
    company_type: str
    team_size: str


@dataclass(frozen=True)
class ServiceCategoryOptionViewModel:
    value: str
    label: str
    selected: bool = False


@dataclass(frozen=True)
class OrganizationServicesFormViewModel:
    service_category_options: tuple[ServiceCategoryOptionViewModel, ...]
