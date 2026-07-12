"""
CustomerProfilePresentationService — Epic 07 (Customer Experience and
Portal Completion).

Role-specific presentation service sitting between domain/application
services (apps.accounts) and the authenticated customer profile
templates. Builds immutable ViewModels only — never returns a model
instance to a view/template. Mirrors
apps.provider_portal.services.profile_service
.ProviderProfilePresentationService's established shape.

Customer profile is deliberately simpler than provider/organization
profile: no avatar/cover upload (CustomerProfile has no media fields —
the existing media foundation, apps.accounts.services.document_service
and CaregiverProfile/OrganizationProfile's avatar/cover_image fields,
was never extended to CustomerProfile, so this service does not invent
one), no verification_status (not modeled for customers), no documents.
"""

from apps.accounts.models.profiles import ProfileStatus
from apps.accounts.services.profiles import calculate_customer_profile_completion

from .viewmodels import (
    CustomerProfileEditFormViewModel,
    CustomerProfileViewModel,
    NavItemViewModel,
    SummaryItemViewModel,
)

STATUS_LABELS = {
    ProfileStatus.DRAFT: "پیش‌نویس",
    ProfileStatus.ACTIVE: "فعال",
    ProfileStatus.SUSPENDED: "معلق",
    ProfileStatus.ARCHIVED: "بایگانی‌شده",
}


class CustomerProfilePresentationService:
    """Read-only: assembles everything the customer profile pages need."""

    @classmethod
    def get_profile_view(cls, *, customer, user) -> CustomerProfileViewModel:
        completion_percent, missing = cls.compute_completion(customer)
        return CustomerProfileViewModel(
            display_name=customer.display_name,
            phone=customer.phone,
            email=user.email or "",
            city=customer.city,
            relation_to_elder=customer.relation_to_elder,
            preferred_contact_method=customer.preferred_contact_method,
            notes=customer.notes,
            is_primary_family_contact=customer.is_primary_family_contact,
            status_label=STATUS_LABELS.get(customer.status, customer.status),
            member_since_label=customer.created_at.strftime("%Y/%m/%d"),
            completion_percent=completion_percent,
            completion_missing_labels=missing,
            summary_items=cls._summary_items(customer),
        )

    @classmethod
    def get_edit_form(cls, customer) -> CustomerProfileEditFormViewModel:
        return CustomerProfileEditFormViewModel(
            display_name=customer.display_name,
            city=customer.city,
            relation_to_elder=customer.relation_to_elder,
            preferred_contact_method=customer.preferred_contact_method,
            notes=customer.notes,
        )

    @classmethod
    def build_nav_items(cls, *, active: str) -> tuple[NavItemViewModel, ...]:
        items = (
            ("dashboard", "داشبورد", "/portal/"),
            ("requests", "درخواست‌های من", "/portal/requests/"),
            ("care-recipients", "گیرندگان خدمت", "/portal/care-recipients/"),
            ("payments", "پرداخت‌ها و فاکتورها", "/portal/payments/"),
            ("reviews", "نظرات من", "/portal/reviews/"),
            ("notifications", "اعلان‌ها", "/portal/notifications/"),
            ("profile", "پروفایل من", "/portal/profile/"),
            ("settings", "تنظیمات حساب", "/portal/settings/"),
        )
        return tuple(NavItemViewModel(label=label, url=url, is_active=(key == active)) for key, label, url in items)

    # ------------------------------------------------------------------

    @staticmethod
    def _summary_items(customer) -> tuple[SummaryItemViewModel, ...]:
        items = []
        if customer.city:
            items.append(SummaryItemViewModel(label="شهر", value=customer.city))
        if customer.preferred_contact_method:
            items.append(SummaryItemViewModel(label="روش تماس ترجیحی", value=customer.preferred_contact_method))
        if customer.relation_to_elder:
            items.append(SummaryItemViewModel(label="نسبت با گیرنده خدمت", value=customer.relation_to_elder))
        return tuple(items)

    @staticmethod
    def compute_completion(customer) -> tuple[int, tuple[str, ...]]:
        """Percent comes from the canonical
        apps.accounts.services.profiles.calculate_customer_profile_completion()
        (pre-existing, previously unused by any caller) — a single source
        of truth for "how complete is this profile". The missing-label
        breakdown mirrors that same function's own field checks, only for
        display purposes; it does not compute its own percentage.
        Public: also reused by CustomerDashboardPresentationService for
        the dashboard's profile-completion summary."""
        percent = calculate_customer_profile_completion(customer)
        checks = [
            ("نام و نام خانوادگی", bool(customer.display_name)),
            ("شهر", bool(customer.city)),
            ("نسبت با گیرنده خدمت", bool(customer.relation_to_elder)),
            ("روش تماس ترجیحی", bool(customer.preferred_contact_method)),
            ("گیرنده خدمت ثبت‌شده", customer.elder_profiles.exists()),
        ]
        missing = tuple(label for label, ok in checks if not ok)
        return percent, missing
