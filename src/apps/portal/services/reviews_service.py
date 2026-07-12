"""
CustomerReviewsPresentationService — Epic 07 (Customer Experience and
Portal Completion).

Assembles the "reviews I've written" page, reusing the new
ReviewSubmissionService.list_for_reviewer() read-only query (Epic 07) —
no new review/rating logic, no mutation.
"""

from apps.reviews.models import ReviewModerationStatus
from apps.reviews.services.review_submission_service import ReviewSubmissionService

from .viewmodels import ReviewRowViewModel

MODERATION_STATUS_LABELS = {
    ReviewModerationStatus.PENDING: "در انتظار بررسی",
    ReviewModerationStatus.APPROVED: "تأییدشده",
    ReviewModerationStatus.REJECTED: "رد شده",
}


class CustomerReviewsPresentationService:
    """Read-only: assembles the customer's own written-reviews list."""

    @classmethod
    def list_reviews(cls, *, tenant_id, reviewer_person_id) -> tuple[ReviewRowViewModel, ...]:
        reviews = ReviewSubmissionService.list_for_reviewer(tenant_id=tenant_id, reviewer_person_id=reviewer_person_id)
        return tuple(cls._row(review) for review in reviews)

    @staticmethod
    def _row(review) -> ReviewRowViewModel:
        return ReviewRowViewModel(
            id=str(review.id),
            supplier_display_name=review.supplier.display_name,
            overall_rating_label=f"{review.overall_rating:.1f}",
            written_text=review.written_text,
            moderation_status_label=MODERATION_STATUS_LABELS.get(review.moderation_status, review.moderation_status),
            created_at_label=review.created_at.strftime("%Y/%m/%d"),
            order_number=review.order.order_number if review.order_id else "",
            order_detail_url=f"/portal/requests/{review.order_id}/" if review.order_id else "",
        )
