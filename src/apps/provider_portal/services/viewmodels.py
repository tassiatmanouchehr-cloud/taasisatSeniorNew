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
class HighlightsViewModel:
    """Sprint 2.3 (Credentials, Skills, Experience, Highlights) — owner-
    side preview of the same derived highlights the public profile shows.
    Every field is computed from data already fetched elsewhere on this
    page; nothing here is persisted or queried freshly."""

    years_experience: int | None
    verified_credential_count: int
    visible_skill_count: int
    visible_experience_count: int


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
    highlights: HighlightsViewModel | None = None


@dataclass(frozen=True)
class SkillRowViewModel:
    id: str
    name: str
    is_visible: bool = True


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
    is_visible: bool = True


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


# ------------------------------------------------------------------
# Sprint 2.5 — Caregiver Professional Dashboard
# ------------------------------------------------------------------


@dataclass(frozen=True)
class DashboardOrderRowViewModel:
    """One order row on the caregiver's own work summary — mirrors
    apps.portal.services.viewmodels.OrderRowViewModel's shape (the
    customer-side equivalent), scoped to the caregiver's own orders only."""

    order_id: str
    order_number: str
    service_category_name: str
    status_label: str
    scheduled_for_label: str
    detail_url: str


@dataclass(frozen=True)
class WorkSummaryViewModel:
    """Order.status-derived counts (current/upcoming/completed/cancelled)
    — see orders.models.OrderStatus for the exact, unmodified state
    machine these groupings come from. current_items/upcoming_items are
    bounded, recent-first lists; the *_count fields are exact totals from
    a single aggregate query, not len() of a possibly-truncated list."""

    current_count: int
    upcoming_count: int
    completed_count: int
    cancelled_count: int
    current_items: tuple[DashboardOrderRowViewModel, ...]
    upcoming_items: tuple[DashboardOrderRowViewModel, ...]
    recent_completed_items: tuple[DashboardOrderRowViewModel, ...]


@dataclass(frozen=True)
class WalletMovementRowViewModel:
    """One apps.wallet.models.WalletTransaction row — transaction_type is
    this model's own existing choice (CREDIT/DEBIT/REFUND/PROMOTION/
    ADJUSTMENT/MANUAL); there is no distinct bonus/penalty type to
    classify against (see FinancialOverviewViewModel.bonus_penalty_note)."""

    transaction_type_label: str
    amount_label: str
    reason: str
    created_at_label: str


@dataclass(frozen=True)
class FinancialOverviewViewModel:
    """available_balance is the wallet's own cached, deterministic
    balance (apps.wallet.models.Wallet.balance, kept in sync by
    WalletService.recalculate_balance() — never recomputed here).
    has_wallet distinguishes "no wallet created yet" from "zero balance."
    bonus_penalty_note is populated only when no canonical bonus/penalty
    representation exists (see this sprint's own ADM entry) — recent
    wallet movements above already show every CREDIT/DEBIT/ADJUSTMENT
    regardless of whether it represents a bonus, a penalty, or neither."""

    has_wallet: bool
    available_balance_label: str
    currency: str
    recent_movements: tuple[WalletMovementRowViewModel, ...]
    bonus_penalty_note: str


@dataclass(frozen=True)
class InvoiceRowViewModel:
    document_type_label: str
    status_label: str
    total_amount_label: str
    created_at_label: str
    order_number: str


@dataclass(frozen=True)
class InvoiceSummaryViewModel:
    """Counts and recent rows drawn from apps.finance.models.FinancialDocument
    rows where this caregiver's own FinancialParty is the beneficiary —
    the party a document pays out to, never the customer/payer side."""

    counts_by_status: dict
    recent_invoices: tuple[InvoiceRowViewModel, ...]


@dataclass(frozen=True)
class DashboardReviewRowViewModel:
    reviewer_name: str
    rating: object  # Decimal
    rating_stars_rounded: int
    written_text: str
    created_at_label: str


@dataclass(frozen=True)
class ReputationOverviewViewModel:
    average_score: object  # Decimal | None
    review_count: int
    recent_reviews: tuple[DashboardReviewRowViewModel, ...]


@dataclass(frozen=True)
class ProfessionalStatisticsViewModel:
    """Every field here is a read-only derived value from an
    already-canonical source, documented per field — never a duplicated
    or independently-defined counter. See this sprint's own
    IMPLEMENTATION_JOURNAL entry ("Statistics Definitions") for the exact
    source of each value."""

    completed_jobs: int
    """apps.reporting.services.provider_report_service.ProviderReportService
    — CLOSED ExecutionSession count (pre-existing, Module 16 definition,
    unchanged by this sprint)."""

    active_assignments: int
    """Same source — ASSIGNED/CONFIRMED SupplierAssignment count."""

    cancelled_orders: int
    """This sprint's own WorkSummaryViewModel.cancelled_count — Order.status
    == CANCELLED, scoped to this supplier."""

    average_rating: object  # Decimal | None
    """apps.reviews.services.reputation_service.ReputationService — the
    same ReputationSnapshot.average_score every other page (including the
    public profile) already reads."""

    verified_credential_count: int
    """apps.accounts.services.public_credential_selector.PublicCredentialSelector
    — the same APPROVED/unexpired/applicable-type count Sprint 2.3's
    highlights already derive; not recomputed with different rules here."""

    visible_skill_count: int
    """CaregiverSkill rows with is_visible=True — the same definition
    Sprint 2.3's highlights already use."""

    visible_gallery_item_count: int
    """CaregiverGalleryItem rows with is_visible=True — the same
    definition the public gallery section already uses."""


@dataclass(frozen=True)
class CaregiverDashboardViewModel:
    """The Sprint 2.5 additions to the caregiver dashboard — work summary,
    financial overview, invoice summary, reputation (with recent
    reviews), and professional statistics. Deliberately does NOT re-wrap
    the dashboard's pre-existing sections (pending assignments, active
    visits, recent notifications) — those remain their own, unchanged,
    already-tested context variables on dashboard_view; this ViewModel is
    additive, not a replacement. Assembled entirely from data already
    resolved by other canonical services; this ViewModel and its
    assembler (CaregiverDashboardPresentationService.build()) perform no
    query of their own."""

    work_summary: WorkSummaryViewModel
    financial_overview: FinancialOverviewViewModel
    invoice_summary: InvoiceSummaryViewModel
    reputation: ReputationOverviewViewModel
    statistics: ProfessionalStatisticsViewModel
