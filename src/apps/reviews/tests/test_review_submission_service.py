from decimal import Decimal

from apps.orders.models import OrderStatus
from apps.reviews.models import Review, ReviewModerationStatus
from apps.reviews.services import ReviewError, ReviewSubmissionService

from .helpers import ReviewsTestCase


class ReviewSubmissionServiceTest(ReviewsTestCase):
    def test_rejects_review_before_order_completed(self):
        self.assertNotEqual(self.order.status, OrderStatus.COMPLETED)

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=self.order,
                reviewer_person_id=self.customer_profile.person_id,
                dimension_scores=self._dimension_scores(),
            )

    def test_creates_review_after_order_completed(self):
        self._complete_order()

        review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
            written_text="Great service.",
        )

        self.assertEqual(review.order_id, self.order.id)
        self.assertEqual(review.supplier_id, self.supplier.id)
        self.assertEqual(review.tenant_id, self.tenant.id)
        self.assertEqual(review.moderation_status, ReviewModerationStatus.PENDING)
        self.assertEqual(review.written_text, "Great service.")
        self.assertEqual(review.ratings.count(), 4)
        self.assertEqual(review.overall_rating, Decimal("4.50"))

    def test_written_text_is_optional(self):
        self._complete_order()

        review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )

        self.assertEqual(review.written_text, "")

    def test_prevents_duplicate_review_for_same_order_and_supplier(self):
        self._complete_order()

        ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=self.order,
                reviewer_person_id=self.customer_profile.person_id,
                dimension_scores=self._dimension_scores(),
            )

        self.assertEqual(Review.objects.filter(order=self.order, supplier=self.supplier).count(), 1)

    def test_rating_bounds_are_enforced(self):
        self._complete_order()

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=self.order,
                reviewer_person_id=self.customer_profile.person_id,
                dimension_scores=self._dimension_scores(QUALITY=6),
            )

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=self.order,
                reviewer_person_id=self.customer_profile.person_id,
                dimension_scores=self._dimension_scores(QUALITY=0),
            )

    def test_requires_at_least_one_dimension(self):
        self._complete_order()

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=self.order,
                reviewer_person_id=self.customer_profile.person_id,
                dimension_scores={},
            )

    def test_unknown_dimension_is_rejected(self):
        self._complete_order()

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=self.order,
                reviewer_person_id=self.customer_profile.person_id,
                dimension_scores={"NOT_A_DIMENSION": 5},
            )

    def test_tenant_is_derived_from_order(self):
        self._complete_order()

        review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )

        self.assertEqual(review.tenant_id, self.order.tenant_id)
        for rating in review.ratings.all():
            self.assertEqual(rating.tenant_id, self.order.tenant_id)
