"""
ReputationService — Module 13 foundation.

Recalculates a supplier's deterministic reputation aggregate from APPROVED
reviews only, and writes through to ServiceSupplier.reputation_score (the
field Discovery/Matching already read directly — no changes needed there).
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Avg, Count

from ..models import RATING_DECIMAL_PLACES, ReputationSnapshot, Review, ReviewModerationStatus

QUANT = Decimal("1").scaleb(-RATING_DECIMAL_PLACES)


def _q(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)


class ReputationService:
    """Recomputes and reads the reputation aggregate for a ServiceSupplier."""

    @classmethod
    @transaction.atomic
    def recalculate_reputation(cls, supplier) -> ReputationSnapshot:
        approved = Review.objects.filter(
            supplier=supplier, moderation_status=ReviewModerationStatus.APPROVED,
        )
        aggregate = approved.aggregate(avg=Avg("overall_rating"), count=Count("id"))
        review_count = aggregate["count"] or 0
        average_score = _q(aggregate["avg"]) if aggregate["avg"] is not None else None

        snapshot, _ = ReputationSnapshot.objects.update_or_create(
            tenant_id=supplier.tenant_id,
            supplier=supplier,
            defaults={"review_count": review_count, "average_score": average_score},
        )

        supplier.reputation_score = average_score
        supplier.save(update_fields=["reputation_score", "version"])

        return snapshot

    @classmethod
    def get_reputation_summary(cls, supplier) -> dict:
        try:
            snapshot = ReputationSnapshot.objects.get(supplier=supplier)
        except ReputationSnapshot.DoesNotExist:
            return {"review_count": 0, "average_score": None}

        return {
            "review_count": snapshot.review_count,
            "average_score": snapshot.average_score,
        }

    @classmethod
    def list_recent_reviews_with_reviewer_names(cls, supplier, *, limit=5):
        """Sprint 2.5 (Caregiver Professional Dashboard) — the same
        APPROVED-only, reviewer-name-resolved shape
        apps.public_site.services.common.reviews_to_viewmodels() already
        uses for the public profile, provided here so
        apps.provider_portal never queries Review/Person directly (its
        own ORM-discipline guardrail forbids that in views.py). Returns
        [(Review, reviewer_display_name), ...], newest first, bounded by
        `limit` — never the full review history."""
        from apps.kernel.models import Person

        reviews = list(
            Review.objects.filter(
                supplier=supplier, moderation_status=ReviewModerationStatus.APPROVED,
            ).order_by("-created_at")[:limit],
        )
        reviewer_ids = [review.reviewer_person_id for review in reviews]
        names = dict(Person.objects.filter(id__in=reviewer_ids).values_list("id", "full_name"))
        return [(review, names.get(review.reviewer_person_id, "کاربر سالمندیار")) for review in reviews]
