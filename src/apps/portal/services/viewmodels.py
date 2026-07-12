"""
Customer portal ViewModels — Epic 07 (Customer Experience and Portal
Completion).

Frozen dataclasses only. Templates in templates/portal/ consume exactly
these — never a CustomerProfile/ElderProfile/Order/FinancialDocument/
Review instance directly, never a raw queryset, for the new pages this
Epic adds. Mirrors apps.provider_portal.services.viewmodels's and
apps.organization_portal.services.viewmodels's established convention
for this same purpose.

Existing pages this Epic does not touch (dashboard's inner sections,
requests list, wizard) keep their pre-existing, already-shipped shape —
see apps/portal/views.py's module docstring for why: this Epic adds new
capability, it does not retroactively rewrite already-working pages.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NavItemViewModel:
    label: str
    url: str
    is_active: bool = False


@dataclass(frozen=True)
class SummaryItemViewModel:
    label: str
    value: str


@dataclass(frozen=True)
class BadgeViewModel:
    label: str
    variant: str


# ------------------------------------------------------------------
# Customer profile
# ------------------------------------------------------------------


@dataclass(frozen=True)
class CustomerProfileViewModel:
    display_name: str
    phone: str
    email: str
    city: str
    relation_to_elder: str
    preferred_contact_method: str
    notes: str
    is_primary_family_contact: bool
    status_label: str
    member_since_label: str
    completion_percent: int
    completion_missing_labels: tuple[str, ...] = field(default_factory=tuple)
    summary_items: tuple[SummaryItemViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CustomerProfileEditFormViewModel:
    display_name: str
    city: str
    relation_to_elder: str
    preferred_contact_method: str
    notes: str


@dataclass(frozen=True)
class CustomerSettingsViewModel:
    phone: str
    email: str
    status_label: str


# ------------------------------------------------------------------
# Care recipient detail
# ------------------------------------------------------------------


@dataclass(frozen=True)
class CareRecipientOrderRowViewModel:
    order_id: str
    order_number: str
    status_label: str
    status_variant: str
    service_category_name: str
    created_at_label: str
    detail_url: str


@dataclass(frozen=True)
class CareRecipientDetailViewModel:
    id: str
    full_name: str
    age_label: str
    relationship_label: str
    mobility_label: str
    gender_label: str
    city: str
    phone: str
    address: str
    care_needs: str
    medical_notes: str
    disabilities: str
    allergies: str
    preferred_caregiver_gender_label: str
    preferred_language: str
    communication_notes: str
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_notes: str
    is_primary: bool
    is_archived: bool
    edit_url: str
    archive_url: str
    orders: tuple[CareRecipientOrderRowViewModel, ...] = field(default_factory=tuple)


# ------------------------------------------------------------------
# Payments / invoices
# ------------------------------------------------------------------


@dataclass(frozen=True)
class PaymentRowViewModel:
    id: str
    document_type_label: str
    status_label: str
    status_variant: str
    total_amount_label: str
    currency: str
    order_number: str
    order_detail_url: str
    issued_at_label: str


@dataclass(frozen=True)
class PaymentsSummaryViewModel:
    wallet_balance_label: str
    wallet_currency: str
    total_paid_label: str
    total_outstanding_label: str
    rows: tuple[PaymentRowViewModel, ...] = field(default_factory=tuple)


# ------------------------------------------------------------------
# Reviews
# ------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewRowViewModel:
    id: str
    supplier_display_name: str
    overall_rating_label: str
    written_text: str
    moderation_status_label: str
    created_at_label: str
    order_number: str
    order_detail_url: str


# ------------------------------------------------------------------
# Dashboard (Part G: role-specific top-level dashboard ViewModel)
# ------------------------------------------------------------------


@dataclass(frozen=True)
class OrderRowViewModel:
    order_id: str
    order_number: str
    service_category_name: str
    status_label: str
    status_variant: str
    created_at_label: str
    scheduled_for_label: str
    detail_url: str


@dataclass(frozen=True)
class CareRecipientSummaryViewModel:
    id: str
    full_name: str
    is_primary: bool
    detail_url: str


@dataclass(frozen=True)
class NotificationRowViewModel:
    channel_label: str
    created_at_label: str
    is_read: bool


@dataclass(frozen=True)
class CustomerDashboardViewModel:
    customer_display_name: str
    recent_orders: tuple[OrderRowViewModel, ...]
    upcoming_visits: tuple[OrderRowViewModel, ...]
    care_recipients: tuple[CareRecipientSummaryViewModel, ...]
    wallet_balance_label: str
    wallet_currency: str
    has_wallet: bool
    recent_notifications: tuple[NotificationRowViewModel, ...]
    unread_notification_count: int
    profile_completion_percent: int
    pending_actions: tuple[str, ...] = field(default_factory=tuple)
