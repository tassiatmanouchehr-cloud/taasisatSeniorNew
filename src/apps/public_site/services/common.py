"""
Shared, read-only enrichment helpers used by directory_service.py,
profile_service.py, and home_service.py.

Deliberately duck-types whatever apps.accounts.services.supplier_bridge
.resolve_supplier_entity()/.resolve_supplier_entities_bulk() returns
instead of importing CaregiverProfile directly — apps.kernel.tests
.test_architecture_guardrails.ServiceSupplierProfileCouplingTest forbids
importing CaregiverProfile/OrganizationProfile outside apps.accounts,
mirroring exactly how apps.discovery.services.search_service
.SupplierSearchService._matches_city() already reads the resolved
entity's attributes via getattr().

Architecture Review remediation (M1/M2, PR #36): all per-supplier entity
resolution and eligibility now goes through bulk_supplier_attrs(), a
single batched pass over a whole candidate list — one CaregiverProfile
query and one OrganizationMembership query total, never one query per
supplier. The single-supplier helpers below (supplier_entity_attrs(),
is_publicly_visible()) are thin wrappers around the same batch function
for the profile page's one-supplier case, so there is exactly one
implementation of both the resolution and the eligibility rule.
"""

from apps.accounts.models.profiles import OrganizationMembership
from apps.accounts.services.supplier_bridge import resolve_supplier_entities_bulk
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

# apps.accounts.models.profiles.OrgMembershipRole.CAREGIVER /
# OrgMembershipStatus.ACTIVE values, duplicated as plain strings for the
# same reason as VERIFICATION_LABELS above — OrganizationMembership itself
# is not restricted by ServiceSupplierProfileCouplingTest (only
# CaregiverProfile/OrganizationProfile are), so the model is imported
# directly, but its TextChoices enum classes are not.
_MEMBERSHIP_CAREGIVER_ROLE = "caregiver"
_MEMBERSHIP_ACTIVE_STATUS = "active"


def bulk_supplier_attrs(suppliers) -> dict:
    """Single batched pass over a whole candidate list: resolves the
    CaregiverProfile behind every supplier (at most 2 queries total, via
    resolve_supplier_entities_bulk()) and, for organization-affiliated
    suppliers, whether their OrganizationMembership is still active (1
    more batched query) — never one query per supplier. Returns
    {supplier.id: attrs_dict}, reused by every caller in this module
    instead of being recomputed."""
    suppliers = list(suppliers)
    entities_by_supplier_id = resolve_supplier_entities_bulk(suppliers)

    caregiver_entities = [entity for entity in entities_by_supplier_id.values() if entity is not None]
    membership_active_by_user_id = _bulk_organization_membership_active(caregiver_entities)

    attrs_by_id = {}
    for supplier in suppliers:
        entity = entities_by_supplier_id.get(supplier.id)
        membership_active = True
        if supplier.supplier_type == SupplierType.ORGANIZATION_PROVIDER:
            user_id = getattr(entity, "user_id", None)
            membership_active = membership_active_by_user_id.get(user_id, False)
        attrs_by_id[supplier.id] = {
            "city": getattr(entity, "city", "") or "",
            "specialty": getattr(entity, "specialty", "") or "",
            "bio": getattr(entity, "bio", "") or "",
            "years_experience": getattr(entity, "years_experience", None),
            "service_radius_km": getattr(entity, "service_radius_km", None),
            "verification_status": getattr(entity, "verification_status", "unverified") or "unverified",
            "profile_status": getattr(entity, "status", "active") or "active",
            "membership_active": membership_active,
        }
    return attrs_by_id


def _bulk_organization_membership_active(caregiver_entities) -> dict:
    """For organization-affiliated caregivers, public visibility requires
    at least one active (non-suspended, non-removed) OrganizationMembership
    with role_type=caregiver — a caregiver whose affiliation was suspended
    must not be presented as an active, bookable provider (Architecture
    Review M2). One batched query regardless of how many caregivers are
    being checked; independent caregivers never reach this function's
    result being consulted (see bulk_supplier_attrs' supplier_type guard)."""
    user_ids = {entity.user_id for entity in caregiver_entities if getattr(entity, "user_id", None)}
    if not user_ids:
        return {}
    active_user_ids = set(
        OrganizationMembership.objects.filter(
            user_id__in=user_ids,
            role_type=_MEMBERSHIP_CAREGIVER_ROLE,
            status=_MEMBERSHIP_ACTIVE_STATUS,
        ).values_list("user_id", flat=True)
    )
    return {user_id: (user_id in active_user_ids) for user_id in user_ids}


def supplier_entity_attrs(supplier):
    """Single-supplier convenience wrapper around bulk_supplier_attrs() —
    used by the public profile page, which only ever resolves one
    supplier, so there is no N+1 concern here; kept as a thin wrapper
    (not a separate implementation) so the resolution and eligibility
    logic exist in exactly one place."""
    return bulk_supplier_attrs([supplier])[supplier.id]


def is_publicly_visible_attrs(attrs) -> bool:
    """Eligibility rule, applied to an already-resolved attrs dict (from
    bulk_supplier_attrs()) — never re-fetches anything."""
    return attrs["profile_status"] == "active" and attrs["membership_active"]


def is_publicly_visible(supplier) -> bool:
    """A supplier is safe to show on a public page only when its own
    ServiceSupplier row's linked CaregiverProfile is active AND — for
    organization-affiliated suppliers — their OrganizationMembership is
    still active. These lifecycles are independent fields/models and can
    diverge (e.g. a suspended caregiver whose ServiceSupplier row was
    never separately deactivated, or an affiliated caregiver whose
    membership was suspended after their supplier row was created)."""
    return is_publicly_visible_attrs(supplier_entity_attrs(supplier))


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


def distinct_cities_from_attrs(attrs_list) -> tuple[str, ...]:
    """Derives the distinct-city list from already-resolved attrs dicts
    (from bulk_supplier_attrs()) — never re-fetches CaregiverProfile rows."""
    cities = (attrs["city"] for attrs in attrs_list)
    return tuple(sorted({city_name for city_name in cities if city_name}))


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
