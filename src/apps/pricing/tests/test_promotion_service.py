"""Tests for PromotionService: creation, conditions, effects, validation."""

from decimal import Decimal

from apps.pricing.models import PromotionConditionType, PromotionEffectType
from apps.pricing.services import PricingError, PromotionService

from .helpers import PricingTestCase


class PromotionServiceTest(PricingTestCase):
    def test_create_promotion(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Spring Sale")
        self.assertTrue(promotion.is_active)
        self.assertFalse(promotion.stackable)

    def test_add_percentage_discount_effect(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Spring Sale")
        effect = PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.PERCENTAGE_DISCOUNT, percentage=Decimal("10"),
        )
        self.assertEqual(effect.percentage, Decimal("10"))
        self.assertEqual(effect.tenant_id, self.tenant.id)

    def test_percentage_discount_requires_percentage(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Spring Sale")
        with self.assertRaises(PricingError):
            PromotionService.add_effect(promotion=promotion, effect_type=PromotionEffectType.PERCENTAGE_DISCOUNT)

    def test_fixed_discount_requires_fixed_amount(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Spring Sale")
        with self.assertRaises(PricingError):
            PromotionService.add_effect(promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT)

    def test_service_category_condition_requires_category(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Category Sale")
        with self.assertRaises(PricingError):
            PromotionService.add_condition(promotion=promotion, condition_type=PromotionConditionType.SERVICE_CATEGORY)

    def test_supplier_condition_requires_supplier(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Supplier Sale")
        with self.assertRaises(PricingError):
            PromotionService.add_condition(promotion=promotion, condition_type=PromotionConditionType.SUPPLIER)

    def test_min_amount_condition_requires_min_amount(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Bulk Sale")
        with self.assertRaises(PricingError):
            PromotionService.add_condition(promotion=promotion, condition_type=PromotionConditionType.MIN_AMOUNT)

    def test_first_order_only_condition_has_no_extra_requirements(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Welcome Discount")
        condition = PromotionService.add_condition(
            promotion=promotion, condition_type=PromotionConditionType.FIRST_ORDER_ONLY,
        )
        self.assertEqual(condition.condition_type, PromotionConditionType.FIRST_ORDER_ONLY)

    def test_deactivate_promotion(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Spring Sale")
        PromotionService.deactivate_promotion(promotion_id=promotion.id)
        promotion.refresh_from_db()
        self.assertFalse(promotion.is_active)
