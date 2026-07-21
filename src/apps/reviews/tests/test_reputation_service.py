from decimal import Decimal

from apps.kernel.models.supplier import SupplierType
from apps.reviews.models import ReputationSnapshot
from apps.reviews.services import ReviewModerationService, ReviewSubmissionService
from apps.reviews.services.reputation_service import ReputationService

from .helpers import ReviewsTestCase


class ReputationServiceTest(ReviewsTestCase):
    def _submit_and_approve(self, *, order, supplier_assignment, dimension_scores):
        order = self._complete_order(order=order, supplier_assignment=supplier_assignment)
        review = ReviewSubmissionService.submit_review(
            order=order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=dimension_scores,
        )
        return ReviewModerationService.approve_review(review.id)

    def test_only_approved_reviews_affect_reputation(self):
        self._complete_order()
        review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )

        snapshot = ReputationService.recalculate_reputation(self.supplier)

        self.assertEqual(snapshot.review_count, 0)
        self.assertIsNone(snapshot.average_score)

        ReviewModerationService.approve_review(review.id)

        snapshot.refresh_from_db()
        self.assertEqual(snapshot.review_count, 1)
        self.assertEqual(snapshot.average_score, Decimal("4.50"))

    def test_rejected_reviews_are_excluded(self):
        self._complete_order()
        review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )
        ReviewModerationService.reject_review(review.id)

        snapshot = ReputationService.recalculate_reputation(self.supplier)

        self.assertEqual(snapshot.review_count, 0)
        self.assertIsNone(snapshot.average_score)

    def test_deterministic_aggregate_across_multiple_reviews(self):
        order2 = self._create_order(tenant=self.tenant, category=self.category, customer_profile=self.customer_profile)
        from apps.booking.services.assignment_service import AssignmentService

        assignment2 = AssignmentService.assign(order_id=order2.id, supplier=self.supplier)

        self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(QUALITY=5, PUNCTUALITY=5, PROFESSIONALISM=5, COMMUNICATION=5),
        )
        self._submit_and_approve(
            order=order2,
            supplier_assignment=assignment2,
            dimension_scores=self._dimension_scores(QUALITY=3, PUNCTUALITY=3, PROFESSIONALISM=3, COMMUNICATION=3),
        )

        snapshot = ReputationService.recalculate_reputation(self.supplier)

        self.assertEqual(snapshot.review_count, 2)
        self.assertEqual(snapshot.average_score, Decimal("4.00"))

        # Recalculating again is deterministic (idempotent) given the same approved reviews.
        snapshot_again = ReputationService.recalculate_reputation(self.supplier)
        self.assertEqual(snapshot_again.average_score, snapshot.average_score)
        self.assertEqual(snapshot_again.review_count, snapshot.review_count)

    def test_supplier_reputation_score_is_updated(self):
        self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(QUALITY=5, PUNCTUALITY=5, PROFESSIONALISM=5, COMMUNICATION=5),
        )

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.reputation_score, Decimal("5.00"))

    def test_supplier_version_is_bumped_on_reputation_update(self):
        original_version = self.supplier.version

        self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(),
        )

        self.supplier.refresh_from_db()
        self.assertGreater(self.supplier.version, original_version)

    def test_get_reputation_summary_with_no_snapshot(self):
        summary = ReputationService.get_reputation_summary(self.supplier)

        self.assertEqual(summary, {"review_count": 0, "average_score": None})

    def test_get_reputation_summary_after_approval(self):
        self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(),
        )

        summary = ReputationService.get_reputation_summary(self.supplier)

        self.assertEqual(summary["review_count"], 1)
        self.assertEqual(summary["average_score"], Decimal("4.50"))

    def test_organization_supplier_reputation(self):
        org_supplier = self._create_supplier(
            tenant=self.tenant,
            supplier_type=SupplierType.ORGANIZATION,
            display_name="Org Supplier",
        )
        org_order = self._create_order(
            tenant=self.tenant, category=self.category, customer_profile=self.customer_profile
        )
        from apps.booking.services.assignment_service import AssignmentService

        org_assignment = AssignmentService.assign(order_id=org_order.id, supplier=org_supplier)

        self._submit_and_approve(
            order=org_order,
            supplier_assignment=org_assignment,
            dimension_scores=self._dimension_scores(QUALITY=4, PUNCTUALITY=4, PROFESSIONALISM=4, COMMUNICATION=4),
        )

        org_supplier.refresh_from_db()
        self.assertEqual(org_supplier.reputation_score, Decimal("4.00"))

        # Independent supplier from setUp is unaffected.
        self.supplier.refresh_from_db()
        self.assertIsNone(self.supplier.reputation_score)

    def test_independent_supplier_reputation(self):
        self.assertEqual(self.supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)

        self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(QUALITY=2, PUNCTUALITY=2, PROFESSIONALISM=2, COMMUNICATION=2),
        )

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.reputation_score, Decimal("2.00"))

    def test_snapshot_is_one_per_supplier(self):
        self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(),
        )
        ReputationService.recalculate_reputation(self.supplier)

        self.assertEqual(ReputationSnapshot.objects.filter(supplier=self.supplier).count(), 1)


class ListRecentReviewsWithReviewerNamesTest(ReviewsTestCase):
    """Sprint 2.5 (Caregiver Professional Dashboard) —
    ReputationService.list_recent_reviews_with_reviewer_names()."""

    def _submit_and_approve(self, *, order, supplier_assignment, dimension_scores):
        from apps.reviews.services import ReviewModerationService, ReviewSubmissionService

        order = self._complete_order(order=order, supplier_assignment=supplier_assignment)
        review = ReviewSubmissionService.submit_review(
            order=order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=dimension_scores,
        )
        return ReviewModerationService.approve_review(review.id)

    def test_no_reviews_returns_empty(self):
        self.assertEqual(ReputationService.list_recent_reviews_with_reviewer_names(self.supplier), [])

    def test_approved_review_appears_with_reviewer_name(self):
        approved = self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(),
        )

        rows = ReputationService.list_recent_reviews_with_reviewer_names(self.supplier)

        self.assertEqual(len(rows), 1)
        review, reviewer_name = rows[0]
        self.assertEqual(review.id, approved.id)
        self.assertEqual(reviewer_name, self.customer_profile.person.full_name)

    def test_pending_review_never_appears(self):
        from apps.reviews.services import ReviewSubmissionService

        self._complete_order()
        ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )

        self.assertEqual(ReputationService.list_recent_reviews_with_reviewer_names(self.supplier), [])

    def test_rejected_review_never_appears(self):
        from apps.reviews.services import ReviewModerationService, ReviewSubmissionService

        self._complete_order()
        review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )
        ReviewModerationService.reject_review(review.id, reason="test")

        self.assertEqual(ReputationService.list_recent_reviews_with_reviewer_names(self.supplier), [])

    def test_limit_bounds_result_set(self):
        from apps.booking.services.assignment_service import AssignmentService

        self._submit_and_approve(
            order=self.order,
            supplier_assignment=self.supplier_assignment,
            dimension_scores=self._dimension_scores(),
        )
        for _ in range(2):
            order = self._create_order(
                tenant=self.tenant, category=self.category, customer_profile=self.customer_profile
            )
            assignment = AssignmentService.assign(order_id=order.id, supplier=self.supplier)
            self._submit_and_approve(
                order=order, supplier_assignment=assignment, dimension_scores=self._dimension_scores()
            )

        rows = ReputationService.list_recent_reviews_with_reviewer_names(self.supplier, limit=2)
        self.assertEqual(len(rows), 2)

    def test_another_suppliers_reviews_never_appear(self):
        other_supplier = self._create_supplier(display_name="Other Supplier")
        self.assertEqual(ReputationService.list_recent_reviews_with_reviewer_names(other_supplier), [])
