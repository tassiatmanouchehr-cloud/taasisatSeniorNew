"""
Confirmed authorization defect fix — Epic 05 (Permission-Key Registry &
Authorization Hardening).

ReviewSubmissionService.submit_review() previously never verified
reviewer_person_id was actually the order's own customer — any
authenticated user in the tenant with the reviews.submit permission could
submit a review for ANY completed order, not just their own. Documented
in technical-debt-register.md ("ReviewSubmissionService
reviewer-vs-order-customer ownership gap") with an exact recommended fix,
now applied.
"""

from apps.reviews.services.errors import ReviewError
from apps.reviews.services.review_submission_service import ReviewSubmissionService

from .helpers import ReviewsTestCase


class ReviewerOwnershipAuthorizationTest(ReviewsTestCase):
    def test_orders_own_customer_can_review(self):
        order = self._complete_order()
        review = ReviewSubmissionService.submit_review(
            order=order, reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )
        self.assertEqual(review.reviewer_person_id, self.customer_profile.person_id)

    def test_a_different_customer_cannot_review_someone_elses_order(self):
        order = self._complete_order()
        other_customer = self._create_customer(tenant=self.tenant, display_name="Other Customer")

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=order, reviewer_person_id=other_customer.person_id,
                dimension_scores=self._dimension_scores(),
            )

    def test_order_with_no_customer_profile_cannot_be_reviewed_by_anyone(self):
        """An operator-created order with no customer_profile set must fail
        closed, not crash on a None dereference."""
        order_without_customer = self._create_order(
            tenant=self.tenant, category=self.category, customer_profile=None,
        )
        supplier_assignment = self._assign_and_prepare(order_without_customer)
        order_without_customer = self._complete_order(order=order_without_customer, supplier_assignment=supplier_assignment)

        with self.assertRaises(ReviewError):
            ReviewSubmissionService.submit_review(
                order=order_without_customer, reviewer_person_id=self.customer_profile.person_id,
                dimension_scores=self._dimension_scores(),
            )

    def _assign_and_prepare(self, order):
        from apps.booking.services.assignment_service import AssignmentService

        return AssignmentService.assign(order_id=order.id, supplier=self.supplier)
