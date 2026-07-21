from apps.reviews.models import Review, ReviewRating
from apps.reviews.services import ReviewModerationService, ReviewSubmissionService
from apps.reviews.services.reputation_service import ReputationService

from .helpers import ReviewsTestCase


class ReviewTenantIsolationTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()

        self.other_category = None
        from apps.orders.models import CatalogStatus, ServiceCategory

        self.other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        self.other_customer = self._create_customer(tenant=self.other_tenant)
        self.other_order = self._create_order(
            tenant=self.other_tenant,
            category=self.other_category,
            customer_profile=self.other_customer,
        )
        self.other_supplier = self._create_supplier(tenant=self.other_tenant)

        from apps.booking.services.assignment_service import AssignmentService

        self.other_assignment = AssignmentService.assign(order_id=self.other_order.id, supplier=self.other_supplier)

        self._complete_order()
        self._complete_order(order=self.other_order, supplier_assignment=self.other_assignment)

        self.review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores=self._dimension_scores(),
        )
        self.other_review = ReviewSubmissionService.submit_review(
            order=self.other_order,
            reviewer_person_id=self.other_customer.person_id,
            dimension_scores=self._dimension_scores(QUALITY=2, PUNCTUALITY=2, PROFESSIONALISM=2, COMMUNICATION=2),
        )

    def test_for_tenant_scopes_reviews(self):
        tenant_reviews = Review.objects.for_tenant(self.tenant.id)
        other_tenant_reviews = Review.objects.for_tenant(self.other_tenant.id)

        self.assertIn(self.review, tenant_reviews)
        self.assertNotIn(self.other_review, tenant_reviews)
        self.assertIn(self.other_review, other_tenant_reviews)
        self.assertNotIn(self.review, other_tenant_reviews)

    def test_for_tenant_scopes_review_ratings(self):
        tenant_ratings = ReviewRating.objects.for_tenant(self.tenant.id)
        other_tenant_ratings = ReviewRating.objects.for_tenant(self.other_tenant.id)

        self.assertTrue(all(r.tenant_id == self.tenant.id for r in tenant_ratings))
        self.assertTrue(all(r.tenant_id == self.other_tenant.id for r in other_tenant_ratings))

    def test_approving_one_tenants_review_does_not_affect_other_tenant_reputation(self):
        ReviewModerationService.approve_review(self.review.id)

        self.supplier.refresh_from_db()
        self.other_supplier.refresh_from_db()

        self.assertIsNotNone(self.supplier.reputation_score)
        self.assertIsNone(self.other_supplier.reputation_score)

    def test_reputation_snapshots_do_not_leak_across_tenants(self):
        ReviewModerationService.approve_review(self.review.id)
        ReviewModerationService.approve_review(self.other_review.id)

        tenant_summary = ReputationService.get_reputation_summary(self.supplier)
        other_summary = ReputationService.get_reputation_summary(self.other_supplier)

        self.assertEqual(tenant_summary["review_count"], 1)
        self.assertEqual(other_summary["review_count"], 1)
        self.assertNotEqual(tenant_summary["average_score"], other_summary["average_score"])
