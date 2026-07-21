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

Sprint 2.3 (Credentials, Skills, Experience, Highlights): skill/experience
rows now surface `is_visible` (the field existed since Phase 2.1; nothing
previously read it here); `_document_rows()` gained an `expiring_soon`
status (`RequiredDocumentPolicy.is_expiring_soon()`, owner-facing only —
never surfaced on the public profile); `_highlights()` is a small,
read-only aggregation over data this method already has in hand.
"""

from django.utils import timezone

from apps.accounts.models.media import DocumentStatus, DocumentType
from apps.accounts.models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.verification_policy import RequiredDocumentPolicy
from apps.kernel.models.supplier import SupplierType
from apps.orders.models import Order, OrderStatus
from apps.orders.services.queries import CatalogQueryService
from apps.reviews.services.reputation_service import ReputationService

from .viewmodels import (
    BadgeViewModel,
    DocumentRowViewModel,
    ExperienceRowViewModel,
    GalleryItemViewModel,
    HighlightsViewModel,
    NavItemViewModel,
    ProviderBasicInfoFormViewModel,
    ProviderProfessionalInfoFormViewModel,
    ProviderProfileViewModel,
    RatingSummaryViewModel,
    ServiceCategoryOptionViewModel,
    SkillRowViewModel,
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
        documents = cls._document_rows(caregiver)
        completion_percent, missing = cls._completion(caregiver, documents)
        is_activated, eligibility = cls._activation_status(caregiver)
        public_credential_labels = cls._public_credential_labels(caregiver)

        if supplier is None:
            # Core Profile-ServiceSupplier Invariant Remediation: a
            # caregiver who has never reached ACTIVE has no ServiceSupplier
            # to read from — merely viewing this own-profile page must not
            # incidentally create one. Every supplier-derived field below
            # takes its not-yet-activated default instead.
            rating = RatingSummaryViewModel(average=None, review_count=0, stars_rounded=0)
            is_org_affiliated = False
            organization_name = ""
            badges = cls._badges(caregiver, is_org_affiliated=False)
            supplier_id = ""
            avatar_status_dot = AVATAR_STATUS_DOTS["offline"]
            availability_label = AVAILABILITY_LABELS["offline"]
            completed_jobs = 0
            service_names: tuple[str, ...] = ()
            public_preview_url = ""
        else:
            rating = cls._rating_summary(supplier)
            is_org_affiliated = cls._is_org_affiliated(supplier)
            organization_name = cls._organization_name(caregiver) if is_org_affiliated else ""
            badges = cls._badges(caregiver, is_org_affiliated=is_org_affiliated)
            supplier_id = str(supplier.id)
            avatar_status_dot = AVATAR_STATUS_DOTS.get(supplier.availability_status, "offline")
            availability_label = AVAILABILITY_LABELS.get(supplier.availability_status, supplier.availability_status)
            completed_jobs = cls._completed_jobs_count(tenant_id=tenant_id, supplier_id=supplier.id)
            service_names = cls._service_names(supplier, tenant_id=tenant_id)
            public_preview_url = f"/find-a-caregiver/{supplier.id}/"

        return ProviderProfileViewModel(
            supplier_id=supplier_id,
            display_name=caregiver.display_name,
            avatar_url=caregiver.avatar.url if caregiver.avatar else "",
            cover_url=caregiver.cover_image.url if caregiver.cover_image else "",
            avatar_status_dot=avatar_status_dot,
            city=caregiver.city,
            specialty=caregiver.specialty,
            bio=caregiver.bio,
            years_experience=caregiver.years_experience,
            service_radius_km=caregiver.service_radius_km,
            is_organization_affiliated=is_org_affiliated,
            organization_name=organization_name,
            availability_label=availability_label,
            verification_status=caregiver.verification_status,
            is_verified=caregiver.verification_status == "verified",
            rating=rating,
            completed_jobs=completed_jobs,
            service_names=service_names,
            badges=badges,
            documents=documents,
            summary_items=cls._summary_items(caregiver),
            completion_percent=completion_percent,
            completion_missing_labels=missing,
            public_preview_url=public_preview_url,
            is_activated=is_activated,
            activation_eligible=eligibility.eligible,
            activation_blocking_reasons=eligibility.reasons,
            activation_profile_status=caregiver.status,
            skills_count=caregiver.skills.count(),
            experience_count=caregiver.experiences.count(),
            public_credential_labels=public_credential_labels,
            gallery_count=caregiver.gallery_items.count(),
            gallery_limit=cls._gallery_limit(),
            highlights=cls._highlights(
                caregiver,
                public_credential_count=len(public_credential_labels),
            ),
        )

    @staticmethod
    def _highlights(caregiver, *, public_credential_count: int) -> HighlightsViewModel:
        """Sprint 2.3 — every input here is either a plain attribute
        already on `caregiver`/`supplier` or a value this method's own
        caller already computed elsewhere in `get_profile_view()`
        (`public_credential_count`); the two `.count()` calls below are
        the only new queries, matching `skills_count`/`experience_count`
        above them (already fixed-cost, already present before this
        sprint) — no per-item loop, no new N+1."""
        return HighlightsViewModel(
            years_experience=caregiver.years_experience,
            verified_credential_count=public_credential_count,
            visible_skill_count=caregiver.skills.filter(is_visible=True).count(),
            visible_experience_count=caregiver.experiences.filter(is_visible=True).count(),
        )

    @staticmethod
    def _gallery_limit() -> int:
        from apps.accounts.services.caregiver_gallery_service import MAX_GALLERY_ITEMS_PER_CAREGIVER

        return MAX_GALLERY_ITEMS_PER_CAREGIVER

    @staticmethod
    def _public_credential_labels(caregiver) -> tuple[str, ...]:
        from apps.accounts.services.public_credential_selector import PublicCredentialSelector

        return tuple(summary.label for summary in PublicCredentialSelector.for_caregiver(caregiver))

    @staticmethod
    def _activation_status(caregiver):
        """Phase 1.3 (Profile Activation and Completion): owner-facing
        activation state + blockers, reusing
        `ActivationEligibilityService`/`ProfileActivationService`'s own
        read-only queries — never recomputed here. `is_activated` is
        derived from `caregiver.status` directly (the sole source of
        truth, Phase 1.3 remediation) — no query needed."""
        from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService
        from apps.accounts.services.profile_activation_service import ProfileActivationService

        is_activated = ProfileActivationService.is_activated(caregiver)
        eligibility = ActivationEligibilityService.evaluate_caregiver(caregiver)
        return is_activated, eligibility

    @classmethod
    def get_basic_info_form(cls, caregiver) -> ProviderBasicInfoFormViewModel:
        return ProviderBasicInfoFormViewModel(display_name=caregiver.display_name, city=caregiver.city)

    @classmethod
    def get_professional_info_form(cls, *, caregiver, supplier, tenant_id) -> ProviderProfessionalInfoFormViewModel:
        # Core Profile-ServiceSupplier Invariant Remediation: a caregiver
        # who has never reached ACTIVE has no ServiceSupplier to read
        # from — merely visiting this edit page must not incidentally
        # create one. Its selection is simply empty until activation.
        selected_ids: set[str] = (
            set() if supplier is None else {str(cid) for cid in (supplier.service_categories or [])}
        )
        categories = CatalogQueryService.list_active_categories(tenant_id=tenant_id).order_by("sort_order", "name")
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
    def get_skills_view(cls, caregiver) -> tuple[SkillRowViewModel, ...]:
        return tuple(
            SkillRowViewModel(id=str(skill.id), name=skill.name, is_visible=skill.is_visible)
            for skill in caregiver.skills.all()
        )

    @classmethod
    def get_experience_view(cls, caregiver) -> tuple[ExperienceRowViewModel, ...]:
        return tuple(cls._experience_row(entry) for entry in caregiver.experiences.all())

    @classmethod
    def get_gallery_view(cls, caregiver) -> tuple[GalleryItemViewModel, ...]:
        return tuple(
            GalleryItemViewModel(
                id=str(item.id),
                image_url=item.image.url if item.image else "",
                caption=item.caption,
                alt_text=item.alt_text,
                is_visible=item.is_visible,
            )
            for item in caregiver.gallery_items.all()
        )

    @staticmethod
    def _experience_row(entry) -> ExperienceRowViewModel:
        start = entry.start_date.strftime("%Y/%m")
        end = "اکنون" if entry.is_current or not entry.end_date else entry.end_date.strftime("%Y/%m")
        return ExperienceRowViewModel(
            id=str(entry.id),
            title=entry.title,
            organization_name=entry.organization_name,
            description=entry.description,
            start_date=entry.start_date,
            end_date=entry.end_date,
            is_current=entry.is_current,
            period_label=f"{start} - {end}",
            is_visible=entry.is_visible,
        )

    @classmethod
    def build_nav_items(cls, *, active: str) -> tuple[NavItemViewModel, ...]:
        items = (
            ("dashboard", "داشبورد", "/provider/"),
            ("assignments", "تخصیص‌ها", "/provider/assignments/"),
            ("availability", "زمان‌بندی", "/provider/availability/"),
            ("profile", "نمایه من", "/provider/profile/"),
            ("company", "سازمان من", "/provider/company/"),
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
            expiring_soon = not expired and RequiredDocumentPolicy.is_expiring_soon(doc)
            if expired:
                status = "expired"
            elif expiring_soon:
                status = "expiring_soon"
            else:
                status = doc.status
            if expired:
                action_message = "این مدرک منقضی شده است — لطفاً نسخه جدیدی بارگذاری کنید."
            elif expiring_soon:
                action_message = "این مدرک به‌زودی منقضی می‌شود — می‌توانید زودتر تمدید کنید."
            else:
                action_message = _DOCUMENT_ACTION_MESSAGES.get(doc.status, "")
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
