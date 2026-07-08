"""
ReviewModerationService — Module 13 foundation.

One-way PENDING -> APPROVED/REJECTED transitions. Approving a review
triggers reputation recalculation immediately (only approved reviews
affect public reputation).
"""

from django.db import transaction
from django.utils import timezone

from ..models import Review, ReviewModerationStatus
from .errors import ReviewError
from .reputation_service import ReputationService


class ReviewModerationService:
    """Moves a Review from PENDING to APPROVED or REJECTED."""

    @classmethod
    @transaction.atomic
    def approve_review(cls, review_id) -> Review:
        review = Review.objects.select_for_update().get(pk=review_id)

        if review.moderation_status != ReviewModerationStatus.PENDING:
            raise ReviewError(
                f"Only pending reviews can be approved (current status: '{review.moderation_status}').",
            )

        review.moderation_status = ReviewModerationStatus.APPROVED
        review.moderated_at = timezone.now()
        review.save(update_fields=["moderation_status", "moderated_at", "updated_at"])

        ReputationService.recalculate_reputation(review.supplier)

        return review

    @classmethod
    @transaction.atomic
    def reject_review(cls, review_id, reason: str = "") -> Review:
        review = Review.objects.select_for_update().get(pk=review_id)

        if review.moderation_status != ReviewModerationStatus.PENDING:
            raise ReviewError(
                f"Only pending reviews can be rejected (current status: '{review.moderation_status}').",
            )

        review.moderation_status = ReviewModerationStatus.REJECTED
        review.moderation_reason = reason
        review.moderated_at = timezone.now()
        review.save(update_fields=["moderation_status", "moderation_reason", "moderated_at", "updated_at"])

        return review
