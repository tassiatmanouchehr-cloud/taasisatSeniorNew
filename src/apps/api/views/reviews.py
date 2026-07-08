"""
Reviews endpoints — Module 17B.

reviewer_person_id always comes from the authenticated user's own
CustomerProfile — never accepted from the request body, so one user can
never submit a review as another.
"""

from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from apps.kernel.models.supplier import ServiceSupplier
from apps.orders.models import Order
from apps.reviews.services import ReputationService, ReviewSubmissionService

from ..permission_keys import REVIEWS_READ, REVIEWS_SUBMIT
from ..permissions import require_permission, resolve_customer_profile
from ..serializers import ReputationSummarySerializer, ReviewSerializer, ReviewSubmitSerializer
from .base import ApiView


class ReviewSubmitView(ApiView):
    """POST /api/v1/reviews/ — submits a review for a completed order."""

    def post(self, request):
        tenant_id = require_permission(request, REVIEWS_SUBMIT)
        customer_profile = resolve_customer_profile(request)

        payload = ReviewSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        order = Order.objects.get(id=data["order_id"], tenant_id=tenant_id)

        review = ReviewSubmissionService.submit_review(
            order=order,
            reviewer_person_id=customer_profile.person_id,
            dimension_scores=data["dimension_scores"],
            written_text=data.get("written_text", ""),
        )

        return Response(ReviewSerializer(review).data, status=HTTP_201_CREATED)


class SupplierReputationView(ApiView):
    """GET /api/v1/suppliers/{supplier_id}/reputation/ — read-only reputation summary."""

    def get(self, request, supplier_id):
        tenant_id = require_permission(request, REVIEWS_READ)
        supplier = ServiceSupplier.objects.get(id=supplier_id, tenant_id=tenant_id)
        summary = ReputationService.get_reputation_summary(supplier)
        return Response(ReputationSummarySerializer(summary).data)
