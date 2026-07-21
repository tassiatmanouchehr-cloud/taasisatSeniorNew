"""Tests proving pricing records and quote generation are tenant-isolated."""

from decimal import Decimal

from apps.pricing.models import PricingRule, Promotion, PromotionEffectType, Quote
from apps.pricing.services import PricingError, PricingRuleService, PromotionService, QuoteService

from .helpers import PricingTestCase


class PricingTenantIsolationTest(PricingTestCase):
    def test_for_tenant_scopes_pricing_rules(self):
        from apps.pricing.models import PricingRuleType

        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="A",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("1"),
        )
        PricingRuleService.create_rule(
            tenant_id=self.other_tenant.id,
            name="B",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("2"),
        )

        self.assertEqual(PricingRule.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(PricingRule.objects.for_tenant(self.other_tenant.id).count(), 1)

    def test_for_tenant_scopes_promotions(self):
        PromotionService.create_promotion(tenant_id=self.tenant.id, name="A")
        PromotionService.create_promotion(tenant_id=self.other_tenant.id, name="B")

        self.assertEqual(Promotion.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(Promotion.objects.for_tenant(self.other_tenant.id).count(), 1)

    def test_for_tenant_scopes_quotes(self):
        QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("1000"),
        )
        self.assertEqual(Quote.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(Quote.objects.for_tenant(self.other_tenant.id).count(), 0)

    def test_other_tenants_pricing_rules_do_not_affect_quote(self):
        from apps.pricing.models import PricingRuleType

        # A generous rule in another tenant must never leak into this tenant's quote.
        PricingRuleService.create_rule(
            tenant_id=self.other_tenant.id,
            name="Other tenant discount",
            rule_type=PricingRuleType.PERCENTAGE_ADJUSTMENT,
            percentage=Decimal("-90"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.total_amount, Decimal("100000.00"))

    def test_other_tenants_promotions_do_not_affect_quote(self):
        other_promotion = PromotionService.create_promotion(tenant_id=self.other_tenant.id, name="Other tenant promo")
        PromotionService.add_effect(
            promotion=other_promotion,
            effect_type=PromotionEffectType.FIXED_DISCOUNT,
            fixed_amount=Decimal("50000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.total_amount, Decimal("100000.00"))

    def test_base_rule_from_other_tenant_is_not_resolved(self):
        from apps.pricing.models import PricingRuleType

        PricingRuleService.create_rule(
            tenant_id=self.other_tenant.id,
            name="Other tenant base",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("999999"),
        )
        with self.assertRaises(PricingError):
            QuoteService.generate_quote(tenant_id=self.tenant.id, service_category=self.category)
