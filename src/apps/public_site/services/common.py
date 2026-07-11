"""
Shared, read-only enrichment helpers used by directory_service.py,
profile_service.py, and home_service.py.

Deliberately duck-types whatever apps.accounts.services.supplier_bridge
.resolve_supplier_entity() returns instead of importing CaregiverProfile
directly — apps.kernel.tests.test_architecture_guardrails
.ServiceSupplierProfileCouplingTest forbids importing CaregiverProfile/
OrganizationProfile outside apps.accounts, mirroring exactly how
apps.discovery.services.search_service.SupplierSearchService._matches_city()
already reads the resolved entity's attributes via getattr().
"""

from apps.accounts.services.supplier_bridge import resolve_supplier_entity
from apps.kernel.models import Person
from apps.kernel.models.supplier import AvailabilityStatus, SupplierType
from apps.orders.models import Order, OrderStatus
from apps.reviews.services.reputation_service import ReputationService

from .viewmodels import RatingSummaryViewModel, ReviewViewModel

AVAILABILITY_LABELS = {
    AvailabilityStatus.AVAILABLE: "در دسترس",
    AvailabilityStatus.BUSY: "مشغول",
    AvailabilityStatus.OFFLINE: "آفلاین",
    AvailabilityStatus.ON_LEAVE: "در مرخصی",
}

# Maps kernel.AvailabilityStatus values onto ui/components/data/avatar.html's
# own status-dot vocabulary (online|offline|busy|away) — kept here, not in
# the template, per this Epic's "no business logic inside templates" rule.
AVATAR_STATUS_DOTS = {
    AvailabilityStatus.AVAILABLE: "online",
    AvailabilityStatus.BUSY: "busy",
    AvailabilityStatus.OFFLINE: "offline",
    AvailabilityStatus.ON_LEAVE: "away",
}

# apps.accounts.models.profiles.VerificationStatus values, duplicated here
# as plain strings (not imported) to stay inside the same guardrail this
# module's docstring describes — CaregiverProfile's own enum class is
# never imported, only string values read off the resolved instance.
VERIFICATION_LABELS = {
    "unverified": "تأییدنشده",
    "pending": "در حال بررسی",
    "verified": "تأییدشده",
    "rejected": "رد شده",
}


def supplier_entity_attrs(supplier):
    """Duck-typed read of the CaregiverProfile behind a supplier — never
    imports the class, only reads the public fields this page needs."""
    entity = resolve_supplier_entity(supplier)
    return {
        "city": getattr(entity, "city", "") or "",
        "specialty": getattr(entity, "specialty", "") or "",
        "bio": getattr(entity, "bio", "") or "",
        "years_experience": getattr(entity, "years_experience", None),
        "service_radius_km": getattr(entity, "service_radius_km", None),
        "verification_status": getattr(entity, "verification_status", "unverified") or "unverified",
        "profile_status": getattr(entity, "status", "active") or "active",
    }


def is_publicly_visible(supplier) -> bool:
    """A supplier is safe to show on a public page only when both its own
    ServiceSupplier row AND the CaregiverProfile behind it are in an
    active state — the two lifecycles are independent fields and can
    diverge (e.g. a suspended caregiver whose ServiceSupplier row was
    never separately deactivated)."""
    return supplier_entity_attrs(supplier)["profile_status"] == "active"


def avatar_initial(display_name: str) -> str:
    stripped = (display_name or "").strip()
    return stripped[0] if stripped else "?"


def availability_label(availability_status: str) -> str:
    return AVAILABILITY_LABELS.get(availability_status, availability_status)


def avatar_status_dot(availability_status: str) -> str:
    return AVATAR_STATUS_DOTS.get(availability_status, "offline")


def verification_label(verification_status: str) -> str:
    return VERIFICATION_LABELS.get(verification_status, verification_status)


def is_organization_affiliated(supplier) -> bool:
    return supplier.supplier_type == SupplierType.ORGANIZATION_PROVIDER


def rating_summary(supplier) -> RatingSummaryViewModel:
    summary = ReputationService.get_reputation_summary(supplier)
    average = summary["average_score"]
    stars_rounded = int(round(average)) if average is not None else 0
    return RatingSummaryViewModel(
        average=average,
        review_count=summary["review_count"],
        stars_rounded=max(0, min(5, stars_rounded)),
    )


def completed_jobs_count(*, tenant_id, supplier_id) -> int:
    return Order.objects.filter(
        tenant_id=tenant_id,
        assigned_supplier_id=supplier_id,
        status=OrderStatus.COMPLETED,
    ).count()


def bio_snippet(bio: str, *, max_length: int = 140) -> str:
    text = (bio or "").strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "…"


def distinct_cities(suppliers) -> tuple[str, ...]:
    candidate_cities = (supplier_entity_attrs(s)["city"] for s in suppliers)
    return tuple(sorted({city_name for city_name in candidate_cities if city_name}))


def reviews_to_viewmodels(reviews) -> tuple[ReviewViewModel, ...]:
    """Resolves each Review's bare reviewer_person_id (deliberately not a
    hard FK — see apps.reviews.models.Review's own docstring) to a
    display name via a single batched Person lookup."""
    reviews = list(reviews)
    reviewer_ids = [review.reviewer_person_id for review in reviews]
    names = dict(Person.objects.filter(id__in=reviewer_ids).values_list("id", "full_name"))

    return tuple(
        ReviewViewModel(
            reviewer_name=names.get(review.reviewer_person_id, "کاربر سالمندیار"),
            rating=review.overall_rating,
            rating_stars_rounded=max(0, min(5, int(round(review.overall_rating)))),
            written_text=review.written_text,
            created_at_display=review.created_at.strftime("%Y/%m/%d"),
        )
        for review in reviews
    )
