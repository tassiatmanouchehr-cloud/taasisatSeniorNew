"""
ProviderProfilePresentationService — Epic 06 Sprint 2 (Shared Portal UI
Core, Provider Profile, Organization Profile).

Role-specific presentation service sitting between domain/application
services (apps.accounts, apps.orders, apps.reviews, apps.availability,
apps.kernel) and the authenticated provider profile templates. Builds
immutable ViewModels only — never returns a model instance to a view/
template. Mirrors apps.public_site.services' established pattern for
this Epic, but for the *authenticated, editable* surface rather than the
public-safe one (compare apps.public_site.services.profile_service
.CaregiverPublicProfileService, which this service deliberately does not
import from — different trust boundary, different ViewModel shape,
intentionally not shared).
"""

from django.utils import timezone

from apps.accounts.models.media import DocumentStatus, DocumentType
from apps.accounts.models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus
from apps.accounts.services.document_service import DocumentService
from apps.kernel.models.supplier import SupplierType
from apps.orders.models import Order, OrderStatus
from apps.orders.services.queries import CatalogQueryService
from apps.reviews.services.reputation_service import ReputationService

from .viewmodels import (
    BadgeViewModel,
    DocumentRowViewModel,
    NavItemViewModel,
    ProviderBasicInfoFormViewModel,
    ProviderProfessionalInfoFormViewModel,
    ProviderProfileViewModel,
    RatingSummaryViewModel,
    ServiceCategoryOptionViewModel,
    SummaryItemViewModel,
)

AVAILABILITY_LABELS = {
    "available": "در دسترس",
    "busy": "مشغول",
    "offline": "آفلاین",
    "on_leave": "در مرخصی",
}

AVATAR_STATUS_DOTS = {
    "available": "online",
    "busy": "busy",
    "offline": "offline",
    "on_leave": "away",
}

VERIFICATION_LABELS = {
    "unverified": "تأییدنشده",
    "pending": "در حال بررسی",
    "verified": "تأییدشده",
    "rejected": "رد شده",
}

PROVIDER_DOCUMENT_TYPES = (
    DocumentType.IDENTITY,
    DocumentType.BACKGROUND_CHECK,
    DocumentType.QUALIFICATION,
    DocumentType.TRAINING_CERTIFICATE,
    DocumentType.LICENSE,
)

DOCUMENT_TYPE_LABELS = {
    DocumentType.IDENTITY: "کارت هویت",
    DocumentType.BACKGROUND_CHECK: "گواهی عدم سوءپیشینه",
    DocumentType.QUALIFICATION: "مدرک تخصصی",
    DocumentType.TRAINING_CERTIFICATE: "گواهی آموزشی",
    DocumentType.LICENSE: "پروانه فعالیت",
}

_DOCUMENT_ACTION_MESSAGES = {
    DocumentStatus.REJECTED: "این مدرک رد شده است — لطفاً نسخه جدیدی بارگذاری کنید.",
    DocumentStatus.PENDING: "",
    DocumentStatus.VERIFIED: "",
}


class ProviderProfilePresentationService:
    """Read-only: assembles everything the provider profile pages need."""

    @classmethod
    def get_profile_view(cls, *, supplier, caregiver, tenant_id) -> ProviderProfileViewModel:
        rating = cls._rating_summary(supplier)
        organization_name = cls._organization_name(caregiver) if cls._is_org_affiliated(supplier) else ""
        badges = cls._badges(caregiver, is_org_affiliated=cls._is_org_affiliated(supplier))
        documents = cls._document_rows(caregiver)
        completion_percent, missing = cls._completion(caregiver, documents)

        return ProviderProfileViewModel(
            supplier_id=str(supplier.id),
            display_name=caregiver.display_name,
            avatar_url=caregiver.avatar.url if caregiver.avatar else "",
            cover_url=caregiver.cover_image.url if caregiver.cover_image else "",
            avatar_status_dot=AVATAR_STATUS_DOTS.get(supplier.availability_status, "offline"),
            city=caregiver.city,
            specialty=caregiver.specialty,
            bio=caregiver.bio,
            years_experience=caregiver.years_experience,
            service_radius_km=caregiver.service_radius_km,
            is_organization_affiliated=cls._is_org_affiliated(supplier),
            organization_name=organization_name,
            availability_label=AVAILABILITY_LABELS.get(supplier.availability_status, supplier.availability_status),
            verification_status=caregiver.verification_status,
            is_verified=caregiver.verification_status == "verified",
            rating=rating,
            completed_jobs=cls._completed_jobs_count(tenant_id=tenant_id, supplier_id=supplier.id),
            service_names=cls._service_names(supplier, tenant_id=tenant_id),
            badges=badges,
            documents=documents,
            summary_items=cls._summary_items(caregiver),
            completion_percent=completion_percent,
            completion_missing_labels=missing,
            public_preview_url=f"/find-a-caregiver/{supplier.id}/",
        )

    @classmethod
    def get_basic_info_form(cls, caregiver) -> ProviderBasicInfoFormViewModel:
        return ProviderBasicInfoFormViewModel(display_name=caregiver.display_name, city=caregiver.city)

    @classmethod
    def get_professional_info_form(cls, *, caregiver, supplier, tenant_id) -> ProviderProfessionalInfoFormViewModel:
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).order_by("sort_order", "name")
        selected_ids = {str(cid) for cid in (supplier.service_categories or [])}
        options = tuple(
            ServiceCategoryOptionViewModel(value=str(cat.id), label=cat.name, selected=str(cat.id) in selected_ids)
            for cat in categories
        )
        return ProviderProfessionalInfoFormViewModel(
            bio=caregiver.bio,
            specialty=caregiver.specialty,
            years_experience=caregiver.years_experience,
            service_radius_km=caregiver.service_radius_km,
            service_category_options=options,
        )

    @classmethod
    def build_nav_items(cls, *, active: str) -> tuple[NavItemViewModel, ...]:
        items = (
            ("dashboard", "داشبورد", "/provider/"),
            ("assignments", "تخصیص‌ها", "/provider/assignments/"),
            ("availability", "زمان‌بندی", "/provider/availability/"),
            ("profile", "نمایه من", "/provider/profile/"),
            ("earnings", "درآمد", "/provider/earnings/"),
            ("notifications", "اعلان‌ها", "/provider/notifications/"),
        )
        return tuple(NavItemViewModel(label=label, url=url, is_active=(key == active)) for key, label, url in items)

    # ------------------------------------------------------------------

    @staticmethod
    def _is_org_affiliated(supplier) -> bool:
        return supplier.supplier_type == SupplierType.ORGANIZATION_PROVIDER

    @staticmethod
    def _organization_name(caregiver) -> str:
        membership = (
            OrganizationMembership.objects.filter(
                user=caregiver.user,
                role_type=OrgMembershipRole.CAREGIVER,
                status=OrgMembershipStatus.ACTIVE,
            )
            .select_related("organization")
            .first()
        )
        return membership.organization.name if membership else ""

    @staticmethod
    def _rating_summary(supplier) -> RatingSummaryViewModel:
        summary = ReputationService.get_reputation_summary(supplier)
        average = summary["average_score"]
        stars_rounded = int(round(average)) if average is not None else 0
        return RatingSummaryViewModel(
            average=average,
            review_count=summary["review_count"],
            stars_rounded=max(0, min(5, stars_rounded)),
        )

    @staticmethod
    def _completed_jobs_count(*, tenant_id, supplier_id) -> int:
        return Order.objects.filter(
            tenant_id=tenant_id,
            assigned_supplier_id=supplier_id,
            status=OrderStatus.COMPLETED,
        ).count()

    @staticmethod
    def _service_names(supplier, *, tenant_id) -> tuple[str, ...]:
        category_ids = supplier.service_categories or []
        if not category_ids:
            return ()
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).filter(id__in=category_ids)
        return tuple(category.name for category in categories.order_by("sort_order", "name"))

    @classmethod
    def _badges(cls, caregiver, *, is_org_affiliated) -> tuple[BadgeViewModel, ...]:
        badges = [
            BadgeViewModel(
                label=VERIFICATION_LABELS.get(caregiver.verification_status, caregiver.verification_status),
                variant="success" if caregiver.verification_status == "verified" else "neutral",
            ),
        ]
        badges.append(BadgeViewModel(label="وابسته به سازمان" if is_org_affiliated else "مستقل", variant="neutral"))
        return tuple(badges)

    @classmethod
    def _document_rows(cls, caregiver) -> tuple[DocumentRowViewModel, ...]:
        existing = {doc.document_type: doc for doc in DocumentService.list_for_caregiver(caregiver)}
        rows = []
        for doc_type in PROVIDER_DOCUMENT_TYPES:
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
                        replace_url=f"/provider/documents/{doc_type}/",
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
                else _DOCUMENT_ACTION_MESSAGES.get(doc.status, "")
            )
            rows.append(
                DocumentRowViewModel(
                    id=str(doc.id),
                    label=label,
                    status=status,
                    expiry_label=doc.expiry_date.strftime("%Y/%m/%d") if doc.expiry_date else "",
                    action_message=action_message,
                    replace_url=f"/provider/documents/{doc_type}/",
                ),
            )
        return tuple(rows)

    @staticmethod
    def _summary_items(caregiver) -> tuple[SummaryItemViewModel, ...]:
        items = []
        if caregiver.city:
            items.append(SummaryItemViewModel(label="شهر", value=caregiver.city))
        if caregiver.years_experience is not None:
            items.append(SummaryItemViewModel(label="سابقه کار", value=f"{caregiver.years_experience} سال"))
        if caregiver.service_radius_km is not None:
            items.append(SummaryItemViewModel(label="شعاع خدمت‌رسانی", value=f"{caregiver.service_radius_km} کیلومتر"))
        return tuple(items)

    @staticmethod
    def _completion(caregiver, documents) -> tuple[int, tuple[str, ...]]:
        checks = [
            ("عکس پروفایل", bool(caregiver.avatar)),
            ("بیوگرافی", bool(caregiver.bio.strip())),
            ("تخصص", bool(caregiver.specialty.strip())),
            ("سابقه کار", caregiver.years_experience is not None),
            ("حداقل یک مدرک تأییدشده", any(doc.status == "verified" for doc in documents)),
        ]
        done = sum(1 for _, ok in checks if ok)
        percent = round((done / len(checks)) * 100) if checks else 0
        missing = tuple(label for label, ok in checks if not ok)
        return percent, missing
