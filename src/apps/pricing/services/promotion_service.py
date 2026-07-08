"""
PromotionService — Module 11 foundation.

The only code that creates Promotion, PromotionCondition, and
PromotionEffect rows. Backend foundation only — no coupon-code redemption,
no campaign UI.
"""

from django.db import transaction

from ..models import Promotion, PromotionCondition, PromotionConditionType, PromotionEffect, PromotionEffectType
from .errors import PricingError


class PromotionService:
    """Creates promotions and their conditions/effects."""

    @classmethod
    def create_promotion(
        cls, *, tenant_id, name, stackable=False, priority=0, starts_at=None, ends_at=None, metadata=None,
    ) -> Promotion:
        return Promotion.objects.create(
            tenant_id=tenant_id,
            name=name,
            stackable=stackable,
            priority=priority,
            starts_at=starts_at,
            ends_at=ends_at,
            metadata=metadata or {},
        )

    @classmethod
    def add_condition(
        cls, *, promotion, condition_type, service_category=None, supplier=None, min_amount=None, metadata=None,
    ) -> PromotionCondition:
        cls._validate_condition(
            condition_type=condition_type, service_category=service_category,
            supplier=supplier, min_amount=min_amount,
        )
        return PromotionCondition.objects.create(
            tenant_id=promotion.tenant_id,
            promotion=promotion,
            condition_type=condition_type,
            service_category=service_category,
            supplier=supplier,
            min_amount=min_amount,
            metadata=metadata or {},
        )

    @classmethod
    def add_effect(
        cls, *, promotion, effect_type, percentage=None, fixed_amount=None, max_discount_amount=None, metadata=None,
    ) -> PromotionEffect:
        cls._validate_effect(effect_type=effect_type, percentage=percentage, fixed_amount=fixed_amount)
        return PromotionEffect.objects.create(
            tenant_id=promotion.tenant_id,
            promotion=promotion,
            effect_type=effect_type,
            percentage=percentage,
            fixed_amount=fixed_amount,
            max_discount_amount=max_discount_amount,
            metadata=metadata or {},
        )

    @classmethod
    @transaction.atomic
    def deactivate_promotion(cls, *, promotion_id) -> Promotion:
        promotion = Promotion.objects.get(id=promotion_id)
        promotion.is_active = False
        promotion.save(update_fields=["is_active", "updated_at"])
        return promotion

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _validate_condition(*, condition_type, service_category, supplier, min_amount) -> None:
        if condition_type == PromotionConditionType.SERVICE_CATEGORY and service_category is None:
            raise PricingError("SERVICE_CATEGORY condition requires service_category.")
        if condition_type == PromotionConditionType.SUPPLIER and supplier is None:
            raise PricingError("SUPPLIER condition requires supplier.")
        if condition_type == PromotionConditionType.MIN_AMOUNT:
            if min_amount is None:
                raise PricingError("MIN_AMOUNT condition requires min_amount.")
            if min_amount < 0:
                raise PricingError("min_amount must not be negative.")

    @staticmethod
    def _validate_effect(*, effect_type, percentage, fixed_amount) -> None:
        if effect_type == PromotionEffectType.PERCENTAGE_DISCOUNT:
            if percentage is None:
                raise PricingError("PERCENTAGE_DISCOUNT effect requires percentage.")
            if percentage < 0:
                raise PricingError("percentage must not be negative.")
        elif effect_type == PromotionEffectType.FIXED_DISCOUNT:
            if fixed_amount is None:
                raise PricingError("FIXED_DISCOUNT effect requires fixed_amount.")
            if fixed_amount < 0:
                raise PricingError("fixed_amount must not be negative.")
        else:
            raise PricingError(f"Unknown effect_type: {effect_type}")
