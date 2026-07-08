from decimal import Decimal

from apps.api.permission_keys import PRICING_QUOTES_CREATE
from apps.pricing.models import Quote

from .helpers import ApiTestCase


class QuoteCreateEndpointTest(ApiTestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post("/api/v1/pricing/quotes/", {"base_amount": "1000"}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_without_permission_is_forbidden(self):
        self.client.force_login(self.actor)
        response = self.client.post("/api/v1/pricing/quotes/", {"base_amount": "1000"}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_creates_quote_with_explicit_base_amount(self):
        self._grant(self.actor, self.tenant, [PRICING_QUOTES_CREATE])
        self.client.force_login(self.actor)

        response = self.client.post(
            "/api/v1/pricing/quotes/",
            {"base_amount": "150000", "service_category_id": str(self.category.id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(Decimal(body["base_amount"]), Decimal("150000.00"))
        self.assertEqual(Quote.objects.filter(tenant=self.tenant).count(), 1)

    def test_missing_base_amount_and_no_rule_maps_to_domain_error(self):
        self._grant(self.actor, self.tenant, [PRICING_QUOTES_CREATE])
        self.client.force_login(self.actor)

        response = self.client.post("/api/v1/pricing/quotes/", {}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "domain_error")

    def test_quote_is_scoped_to_actors_own_tenant(self):
        self._grant(self.actor, self.tenant, [PRICING_QUOTES_CREATE])
        self.client.force_login(self.actor)

        self.client.post(
            "/api/v1/pricing/quotes/", {"base_amount": "1000"}, content_type="application/json",
        )

        quote = Quote.objects.get()
        self.assertEqual(quote.tenant_id, self.tenant.id)

    def test_unknown_service_category_in_another_tenant_404s(self):
        self._grant(self.actor, self.tenant, [PRICING_QUOTES_CREATE])
        self.client.force_login(self.actor)

        from apps.orders.models import CatalogStatus, ServiceCategory
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant, name="Other", slug="other", status=CatalogStatus.ACTIVE,
        )

        response = self.client.post(
            "/api/v1/pricing/quotes/",
            {"base_amount": "1000", "service_category_id": str(other_category.id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
