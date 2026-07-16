"""
OrganizationProfilePresentationService — Epic 06 Sprint 2 (Shared Portal
UI Core, Provider Profile, Organization Profile).

Role-specific presentation service for the authenticated organization
profile pages. Deliberately does not import from
apps.provider_portal.services (no shared business ownership between the
two portals, only shared visual components) nor from
apps.public_site.services (different trust boundary/ViewModel shape —
see that module's own profile_service.py for the public-safe counterpart
this service's public_preview_url points at).
"""

from django.utils import timezone

from apps.accounts.models.media import DocumentStatus, DocumentType
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
from apps.orders.services.queries import CatalogQueryService
from apps.reviews.services.reputation_service import ReputationService

from .viewmodels import (
    BadgeViewModel,
    DocumentRowViewModel,
    NavItemViewModel,
    OrganizationProfileFormViewModel,
    OrganizationProfileViewModel,
    OrganizationServicesFormViewModel,
    RatingSummaryViewModel,
    ServiceCategoryOptionViewModel,
    SummaryItemViewModel,
)

VERIFICATION_LABELS = {
    "unverified": "تأییدنشده",
    "pending": "در حال بررسی",
    "verified": "تأییدشده",
    "rejected": "رد شده",
}

ORGANIZATION_DOCUMENT_TYPES = (
    DocumentType.REGISTRATION,
    DocumentType.OPERATING_LICENSE,
    DocumentType.INSURANCE,
    DocumentType.PROFESSIONAL_PERMIT,
)

DOCUMENT_TYPE_LABELS = {
    DocumentType.REGISTRATION: "مدرک ثبت شرکت",
    DocumentType.OPERATING_LICENSE: "پروانه فعالیت",
    DocumentType.INSURANCE: "بیمه‌نامه",
    DocumentType.PROFESSIONAL_PERMIT: "مجوز حرفه‌ای",
}


class OrganizationProfilePresentationService:
    """Read-only: assembles everything the organization profile pages need."""

    @classmethod
    def get_profile_view(cls, *, organization, tenant_id) -> OrganizationProfileViewModel:
        supplier = get_or_create_supplier_for_organization(organization, tenant_id=tenant_id)
        rating = cls._rating_summary(supplier)
        documents = cls._document_rows(organization)
        active_provider_count = OrganizationStaffService.list_active_caregivers(organization).count()
        completion_percent, missing = cls._completion(organization, documents)
        is_activated, eligibility = cls._activation_status(organization)

        return OrganizationProfileViewModel(
            organization_id=str(organization.id),
            name=organization.name,
            headline=organization.headline,
            logo_url=organization.logo.url if organization.logo else "",
            cover_url=organization.cover_image.url if organization.cover_image else "",
            city=organization.city,
            description=organization.description,
            phone=organization.phone,
            address=organization.address,
            verification_status=organization.verification_status,
            is_verified=organization.verification_status == "verified",
            active_provider_count=active_provider_count,
            rating=rating,
            service_names=cls._service_names(supplier, tenant_id=tenant_id),
            badges=(
                BadgeViewModel(
                    label=VERIFICATION_LABELS.get(organization.verification_status, organization.verification_status),
                    variant="success" if organization.verification_status == "verified" else "neutral",
                ),
            ),
            documents=documents,
            summary_items=cls._summary_items(organization, active_provider_count),
            completion_percent=completion_percent,
            completion_missing_labels=missing,
            public_preview_url=f"/find-an-organization/{supplier.id}/",
            is_activated=is_activated,
            activation_eligible=eligibility.eligible,
            activation_blocking_reasons=eligibility.reasons,
            activation_profile_status=organization.status,
        )

    @staticmethod
    def _activation_status(organization):
        """Phase 1.3 (Profile Activation and Completion): owner-facing
        activation state + blockers, reusing
        `ActivationEligibilityService`/`ProfileActivationService`'s own
        read-only queries — never recomputed here. `is_activated` is
        derived from `organization.status` directly (the sole source of
        truth, Phase 1.3 remediation) — no query needed."""
        from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService
        from apps.accounts.services.profile_activation_service import ProfileActivationService

        is_activated = ProfileActivationService.is_activated(organization)
        eligibility = ActivationEligibilityService.evaluate_organization(organization)
        return is_activated, eligibility

    @classmethod
    def get_profile_form(cls, organization) -> OrganizationProfileFormViewModel:
        return OrganizationProfileFormViewModel(
            name=organization.name,
            headline=organization.headline,
            description=organization.description,
            city=organization.city,
            phone=organization.phone,
            address=organization.address,
            company_type=organization.company_type,
            team_size=organization.team_size,
        )

    @classmethod
    def get_services_form(cls, organization, *, tenant_id) -> OrganizationServicesFormViewModel:
        supplier = get_or_create_supplier_for_organization(organization, tenant_id=tenant_id)
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).order_by("sort_order", "name")
        selected_ids = {str(cid) for cid in (supplier.service_categories or [])}
        options = tuple(
            ServiceCategoryOptionViewModel(value=str(cat.id), label=cat.name, selected=str(cat.id) in selected_ids)
            for cat in categories
        )
        return OrganizationServicesFormViewModel(service_category_options=options)

    @classmethod
    def build_nav_items(cls, *, active: str) -> tuple[NavItemViewModel, ...]:
        items = (
            ("dashboard", "داشبورد", "/organization/"),
            ("profile", "نمایه سازمان", "/organization/profile/"),
            ("staff", "نیروها", "/organization/staff/"),
            ("assignment-center", "مرکز تخصیص", "/organization/assignments/"),
            ("capacity", "ظرفیت", "/organization/capacity/"),
            ("financial", "وضعیت مالی", "/organization/financial/"),
            ("reports", "گزارش‌ها", "/organization/reports/"),
            ("notifications", "اعلان‌ها", "/organization/notifications/"),
        )
        return tuple(NavItemViewModel(label=label, url=url, is_active=(key == active)) for key, label, url in items)

    # ------------------------------------------------------------------

    @staticmethod
    def _rating_summary(supplier) -> RatingSummaryViewModel:
        summary = ReputationService.get_reputation_summary(supplier)
        return RatingSummaryViewModel(average=summary["average_score"], review_count=summary["review_count"])

    @staticmethod
    def _service_names(supplier, *, tenant_id) -> tuple[str, ...]:
        category_ids = supplier.service_categories or []
        if not category_ids:
            return ()
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).filter(id__in=category_ids)
        return tuple(category.name for category in categories.order_by("sort_order", "name"))

    @classmethod
    def _document_rows(cls, organization) -> tuple[DocumentRowViewModel, ...]:
        existing = {doc.document_type: doc for doc in DocumentService.list_for_organization(organization)}
        rows = []
        for doc_type in ORGANIZATION_DOCUMENT_TYPES:
            label = DOCUMENT_TYPE_LABELS[doc_type]
            doc = existing.get(doc_type)
            if doc is None:
                rows.append(
                    DocumentRowViewModel(
                        id="",
                        label=label,
                        status="unverified",
                        expiry_label="",
                        action_message="هنوز بارگذاری نشده است.",
                        replace_url=f"/organization/documents/{doc_type}/",
                    ),
                )
                continue
            expired = (
                doc.status == DocumentStatus.VERIFIED
                and doc.expiry_date is not None
                and doc.expiry_date < timezone.now().date()
            )
            status = "expired" if expired else doc.status
            action_message = (
                "این مدرک منقضی شده است — لطفاً نسخه جدیدی بارگذاری کنید."
                if expired
                else (
                    "این مدرک رد شده است — لطفاً نسخه جدیدی بارگذاری کنید."
                    if doc.status == DocumentStatus.REJECTED
                    else ""
                )
            )
            rows.append(
                DocumentRowViewModel(
                    id=str(doc.id),
                    label=label,
                    status=status,
                    expiry_label=doc.expiry_date.strftime("%Y/%m/%d") if doc.expiry_date else "",
                    action_message=action_message,
                    replace_url=f"/organization/documents/{doc_type}/",
                ),
            )
        return tuple(rows)

    @staticmethod
    def _summary_items(organization, active_provider_count) -> tuple[SummaryItemViewModel, ...]:
        items = []
        if organization.city:
            items.append(SummaryItemViewModel(label="شهر", value=organization.city))
        if organization.company_type:
            items.append(SummaryItemViewModel(label="نوع فعالیت", value=organization.company_type))
        items.append(SummaryItemViewModel(label="مراقبان فعال", value=str(active_provider_count)))
        return tuple(items)

    @staticmethod
    def _completion(organization, documents) -> tuple[int, tuple[str, ...]]:
        checks = [
            ("لوگو", bool(organization.logo)),
            ("توضیحات", bool(organization.description.strip())),
            ("اطلاعات تماس", bool(organization.phone.strip())),
            ("آدرس", bool(organization.address.strip())),
            ("حداقل یک مدرک تأییدشده", any(doc.status == "verified" for doc in documents)),
        ]
        done = sum(1 for _, ok in checks if ok)
        percent = round((done / len(checks)) * 100) if checks else 0
        missing = tuple(label for label, ok in checks if not ok)
        return percent, missing
