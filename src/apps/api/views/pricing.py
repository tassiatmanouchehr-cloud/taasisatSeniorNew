"""
Pricing endpoint — Module 17B.

The view's only job is resolving IDs from the request body into
tenant-scoped ORM objects (plain .get() lookups — not business logic) and
handing them to QuoteService.generate_quote(), which owns every pricing
rule. No payment/booking side effects.
"""

from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from apps.kernel.models.supplier import ServiceSupplier
from apps.orders.models import Order, ServiceCategory
from apps.pricing.services import QuoteService

from ..permission_keys import PRICING_QUOTES_CREATE
from ..permissions import require_permission
from ..serializers import QuoteRequestSerializer, QuoteSerializer
from .base import ApiView


class QuoteCreateView(ApiView):
    """POST /api/v1/pricing/quotes/ — creates a Quote. No payment/booking side effects."""

    def post(self, request):
        tenant_id = require_permission(request, PRICING_QUOTES_CREATE)

        payload = QuoteRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        service_category = None
        if data.get("service_category_id"):
            service_category = ServiceCategory.objects.get(id=data["service_category_id"], tenant_id=tenant_id)

        supplier = None
        if data.get("supplier_id"):
            supplier = ServiceSupplier.objects.get(id=data["supplier_id"], tenant_id=tenant_id)

        order = None
        if data.get("order_id"):
            order = Order.objects.get(id=data["order_id"], tenant_id=tenant_id)

        quote = QuoteService.generate_quote(
            tenant_id=tenant_id,
            service_category=service_category,
            supplier=supplier,
            order=order,
            base_amount=data.get("base_amount"),
            duration_hours=data.get("duration_hours"),
            currency=data.get("currency") or None,
            metadata=data.get("metadata"),
        )

        return Response(QuoteSerializer(quote).data, status=HTTP_201_CREATED)
