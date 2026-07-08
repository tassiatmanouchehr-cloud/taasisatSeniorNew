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
