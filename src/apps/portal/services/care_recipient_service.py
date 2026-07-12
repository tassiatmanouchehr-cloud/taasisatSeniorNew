"""
CareRecipientPresentationService — Epic 07 (Customer Experience and
Portal Completion).

Builds the read-only Care Recipient detail ViewModel. Ownership/tenant
scoping is never re-derived here — the view resolves the ElderProfile
via apps.accounts.services.care_recipients.CareRecipientService
.get_for_customer() first (the same ownership-safe lookup
care_recipient_edit_view already uses), then hands the already-scoped
instance to this service. This service performs no additional ORM
writes and no ownership checks of its own — it only presents.
"""

from django.utils import timezone

from apps.accounts.models.profiles import (
    CaregiverGenderPreference,
    CareRecipientRelationship,
    MobilityLevel,
    ProfileStatus,
)
from apps.orders.models import OrderStatus
from apps.orders.services.queries import OrderQueryService

from .viewmodels import CareRecipientDetailViewModel, CareRecipientOrderRowViewModel

_ORDER_STATUS_VARIANTS = {
    OrderStatus.COMPLETED: "success",
    OrderStatus.CANCELLED: "danger",
    OrderStatus.IN_PROGRESS: "primary",
    OrderStatus.WAITING_SERVICE: "warning",
    OrderStatus.NEW: "neutral",
    OrderStatus.PENDING_OPERATOR_REVIEW: "neutral",
    OrderStatus.CANCELLATION_REQUESTED: "warning",
}

# CareRecipientRelationship, MobilityLevel, and CaregiverGenderPreference
# carry English-only verbose_names (ADR-008 named the vocabulary but never
# localized it) — mapped to Persian here, outside the template, matching
# how CustomerPaymentsPresentationService/CustomerReviewsPresentationService
# already localize their own English-only model choices.
RELATIONSHIP_LABELS = {
    CareRecipientRelationship.SELF: "خودم",
    CareRecipientRelationship.FATHER: "پدر",
    CareRecipientRelationship.MOTHER: "مادر",
    CareRecipientRelationship.SPOUSE: "همسر",
    CareRecipientRelationship.CHILD: "فرزند",
    CareRecipientRelationship.SIBLING: "خواهر/برادر",
    CareRecipientRelationship.GRANDPARENT: "پدربزرگ/مادربزرگ",
    CareRecipientRelationship.RELATIVE: "بستگان",
    CareRecipientRelationship.FRIEND: "دوست",
    CareRecipientRelationship.LEGAL_GUARDIAN: "سرپرست قانونی",
    CareRecipientRelationship.OTHER: "سایر",
}

MOBILITY_LABELS = {
    MobilityLevel.INDEPENDENT: "مستقل",
    MobilityLevel.NEEDS_ASSISTANCE: "نیازمند کمک",
    MobilityLevel.WHEELCHAIR: "استفاده از ویلچر",
    MobilityLevel.BEDRIDDEN: "بستری در تخت",
    MobilityLevel.UNKNOWN: "نامشخص",
}

CAREGIVER_GENDER_LABELS = {
    CaregiverGenderPreference.NO_PREFERENCE: "بدون ترجیح",
    CaregiverGenderPreference.MALE: "مرد",
    CaregiverGenderPreference.FEMALE: "زن",
}


class CareRecipientPresentationService:
    """Read-only: assembles the care recipient detail page."""

    @classmethod
    def get_detail_view(cls, *, customer, care_recipient, tenant_id) -> CareRecipientDetailViewModel:
        orders = OrderQueryService.list_for_care_recipient(
            customer_profile=customer,
            elder_profile=care_recipient,
            tenant_id=tenant_id,
        )
        return CareRecipientDetailViewModel(
            id=str(care_recipient.id),
            full_name=care_recipient.full_name,
            age_label=cls._age_label(care_recipient),
            relationship_label=RELATIONSHIP_LABELS.get(care_recipient.relationship, ""),
            mobility_label=MOBILITY_LABELS.get(care_recipient.mobility_level, ""),
            gender_label=care_recipient.gender,
            city=care_recipient.city,
            phone=care_recipient.phone,
            address=care_recipient.address,
            care_needs=care_recipient.care_needs,
            medical_notes=care_recipient.medical_notes,
            disabilities=care_recipient.disabilities,
            allergies=care_recipient.allergies,
            preferred_caregiver_gender_label=CAREGIVER_GENDER_LABELS.get(care_recipient.preferred_caregiver_gender, ""),
            preferred_language=care_recipient.preferred_language,
            communication_notes=care_recipient.communication_notes,
            emergency_contact_name=care_recipient.emergency_contact_name,
            emergency_contact_phone=care_recipient.emergency_contact_phone,
            emergency_notes=care_recipient.emergency_notes,
            is_primary=care_recipient.is_primary,
            is_archived=care_recipient.status == ProfileStatus.ARCHIVED,
            edit_url=f"/portal/care-recipients/{care_recipient.id}/edit/",
            archive_url=f"/portal/care-recipients/{care_recipient.id}/archive/",
            orders=tuple(cls._order_row(order) for order in orders),
        )

    @staticmethod
    def _age_label(care_recipient) -> str:
        if care_recipient.birth_date:
            today = timezone.now().date()
            age = (
                today.year
                - care_recipient.birth_date.year
                - ((today.month, today.day) < (care_recipient.birth_date.month, care_recipient.birth_date.day))
            )
            return f"{age} سال"
        if care_recipient.approximate_age:
            return f"حدود {care_recipient.approximate_age} سال"
        return ""

    @staticmethod
    def _order_row(order) -> CareRecipientOrderRowViewModel:
        return CareRecipientOrderRowViewModel(
            order_id=str(order.id),
            order_number=order.order_number,
            status_label=order.get_status_display(),
            status_variant=_ORDER_STATUS_VARIANTS.get(order.status, "neutral"),
            service_category_name=order.service_category.name if order.service_category_id else "",
            created_at_label=order.created_at.strftime("%Y/%m/%d"),
            detail_url=f"/portal/requests/{order.id}/",
        )
