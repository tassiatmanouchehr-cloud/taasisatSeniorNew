from decimal import Decimal

from apps.api.permission_keys import REVIEWS_READ, REVIEWS_SUBMIT
from apps.reviews.models import Review

from .helpers import ApiTestCase


class ReviewSubmitEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post("/api/v1/reviews/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_without_permission_is_forbidden(self):
        self.client.force_login(self.customer_profile.user)
        response = self.client.post("/api/v1/reviews/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_submits_review_for_completed_order_as_the_authenticated_customer(self):
        self._grant(self.customer_profile.user, self.tenant, [REVIEWS_SUBMIT])
        self._complete_order()
        self.client.force_login(self.customer_profile.user)

        response = self.client.post(
            "/api/v1/reviews/",
            {
                "order_id": str(self.order.id),
                "dimension_scores": {"QUALITY": 5, "PUNCTUALITY": 4},
                "written_text": "Great service",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["supplier_id"], str(self.supplier.id))

        review = Review.objects.get()
        self.assertEqual(review.reviewer_person_id, self.customer_profile.person_id)
        self.assertEqual(review.tenant_id, self.tenant.id)

    def test_review_before_completion_maps_to_domain_error(self):
        self._grant(self.customer_profile.user, self.tenant, [REVIEWS_SUBMIT])
        self.client.force_login(self.customer_profile.user)

        response = self.client.post(
            "/api/v1/reviews/",
            {"order_id": str(self.order.id), "dimension_scores": {"QUALITY": 5}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "domain_error")

    def test_order_in_another_tenant_404s(self):
        self._grant(self.customer_profile.user, self.tenant, [REVIEWS_SUBMIT])
        self.client.force_login(self.customer_profile.user)

        other_customer = self._create_customer(tenant=self.other_tenant, display_name="Other")
        from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        other_order = Order.objects.create(
            tenant=self.other_tenant, source=OrderSource.OPERATOR, status=OrderStatus.COMPLETED,
            service_category=other_category, customer_profile=other_customer,
            description="x", city="tehran", address="addr", phone="09120000099",
        )

        response = self.client.post(
            "/api/v1/reviews/",
            {"order_id": str(other_order.id), "dimension_scores": {"QUALITY": 5}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)


class SupplierReputationEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(f"/api/v1/suppliers/{self.supplier.id}/reputation/")
        self.assertEqual(response.status_code, 401)

    def test_returns_zeroed_summary_with_no_reviews(self):
        self._grant(self.actor, self.tenant, [REVIEWS_READ])
        self.client.force_login(self.actor)

        response = self.client.get(f"/api/v1/suppliers/{self.supplier.id}/reputation/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["review_count"], 0)
        self.assertIsNone(body["average_score"])

    def test_reflects_approved_review(self):
        from apps.reviews.services import ReviewModerationService, ReviewSubmissionService

        self._grant(self.customer_profile.user, self.tenant, [REVIEWS_SUBMIT])
        self._grant(self.actor, self.tenant, [REVIEWS_READ])
        self._complete_order()

        review = ReviewSubmissionService.submit_review(
            order=self.order, reviewer_person_id=self.customer_profile.person_id,
            dimension_scores={"QUALITY": 4, "PUNCTUALITY": 4},
        )
        ReviewModerationService.approve_review(review.id)

        self.client.force_login(self.actor)
        response = self.client.get(f"/api/v1/suppliers/{self.supplier.id}/reputation/")

        body = response.json()
        self.assertEqual(body["review_count"], 1)
        self.assertEqual(Decimal(body["average_score"]), Decimal("4.00"))

    def test_supplier_in_another_tenant_404s(self):
        self._grant(self.actor, self.tenant, [REVIEWS_READ])
        self.client.force_login(self.actor)

        other_supplier = self._create_supplier(tenant=self.other_tenant, display_name="Other")

        response = self.client.get(f"/api/v1/suppliers/{other_supplier.id}/reputation/")
        self.assertEqual(response.status_code, 404)
