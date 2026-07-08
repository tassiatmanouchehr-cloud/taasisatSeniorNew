from apps.reviews.models import ReviewModerationStatus
from apps.reviews.services import ReviewError, ReviewModerationService, ReviewSubmissionService

from .helpers import ReviewsTestCase


class ReviewModerationServiceTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        self._complete_order()
        self.review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )

    def test_approve_pending_review(self):
        review = ReviewModerationService.approve_review(self.review.id)

        self.assertEqual(review.moderation_status, ReviewModerationStatus.APPROVED)
        self.assertIsNotNone(review.moderated_at)

    def test_reject_pending_review(self):
        review = ReviewModerationService.reject_review(self.review.id, reason="Spam content")

        self.assertEqual(review.moderation_status, ReviewModerationStatus.REJECTED)
        self.assertEqual(review.moderation_reason, "Spam content")
        self.assertIsNotNone(review.moderated_at)

    def test_cannot_approve_already_approved_review(self):
        ReviewModerationService.approve_review(self.review.id)

        with self.assertRaises(ReviewError):
            ReviewModerationService.approve_review(self.review.id)

    def test_cannot_reject_already_approved_review(self):
        ReviewModerationService.approve_review(self.review.id)

        with self.assertRaises(ReviewError):
            ReviewModerationService.reject_review(self.review.id)

    def test_cannot_approve_already_rejected_review(self):
        ReviewModerationService.reject_review(self.review.id)

        with self.assertRaises(ReviewError):
            ReviewModerationService.approve_review(self.review.id)
