"""
PricingRuleService — Module 11 foundation.

The only code that creates/updates/deactivates PricingRule rows. Validates
that each rule carries the fields its rule_type actually needs before it
can ever be evaluated by QuoteService.
"""

from ..models import PricingRule, PricingRuleType
from .errors import PricingError

_AMOUNT_ONLY_TYPES = (PricingRuleType.FIXED_AMOUNT, PricingRuleType.HOURLY_RATE, PricingRuleType.FLAT_SURCHARGE)
_SURCHARGE_GATED_TYPES = (
    PricingRuleType.TIME_OF_DAY_SURCHARGE,
    PricingRuleType.WEEKEND_SURCHARGE,
    PricingRuleType.HOLIDAY_SURCHARGE,
)


class PricingRuleService:
    """Creates, updates, and deactivates PricingRule rows."""

    @classmethod
    def create_rule(
        cls,
        *,
        tenant_id,
        name,
        rule_type,
        service_category=None,
        supplier=None,
        amount=None,
        percentage=None,
        time_start=None,
        time_end=None,
        priority=0,
        currency=None,
        metadata=None,
    ) -> PricingRule:
        cls._validate(
            rule_type=rule_type,
            amount=amount,
            percentage=percentage,
            time_start=time_start,
            time_end=time_end,
        )

        from .. import models as pricing_models

        return PricingRule.objects.create(
            tenant_id=tenant_id,
            name=name,
            rule_type=rule_type,
            service_category=service_category,
            supplier=supplier,
            amount=amount,
            percentage=percentage,
            time_start=time_start,
            time_end=time_end,
            priority=priority,
            currency=currency or pricing_models.DEFAULT_CURRENCY,
            metadata=metadata or {},
        )

    @classmethod
    def update_rule(cls, *, rule_id, **fields) -> PricingRule:
        rule = PricingRule.objects.select_for_update().get(id=rule_id)

        for field, value in fields.items():
            setattr(rule, field, value)

        cls._validate(
            rule_type=rule.rule_type,
            amount=rule.amount,
            percentage=rule.percentage,
            time_start=rule.time_start,
            time_end=rule.time_end,
        )
        rule.save()
        return rule

    @classmethod
    def deactivate_rule(cls, *, rule_id) -> PricingRule:
        rule = PricingRule.objects.get(id=rule_id)
        rule.is_active = False
        rule.save(update_fields=["is_active", "updated_at"])
        return rule

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _validate(*, rule_type, amount, percentage, time_start, time_end) -> None:
        if rule_type in _AMOUNT_ONLY_TYPES:
            if amount is None:
                raise PricingError(f"{rule_type} requires 'amount'.")
            if amount < 0:
                raise PricingError("amount must not be negative.")
            return

        if rule_type == PricingRuleType.PERCENTAGE_ADJUSTMENT:
            if percentage is None:
                raise PricingError("PERCENTAGE_ADJUSTMENT requires 'percentage'.")
            return

        if rule_type in _SURCHARGE_GATED_TYPES:
            if amount is None and percentage is None:
                raise PricingError(f"{rule_type} requires 'amount' or 'percentage'.")
            if amount is not None and amount < 0:
                raise PricingError("amount must not be negative for a surcharge.")
            if percentage is not None and percentage < 0:
                raise PricingError("percentage must not be negative for a surcharge.")
            if rule_type == PricingRuleType.TIME_OF_DAY_SURCHARGE:
                if time_start is None or time_end is None:
                    raise PricingError("TIME_OF_DAY_SURCHARGE requires time_start and time_end.")
                if time_start >= time_end:
                    raise PricingError("time_start must be strictly before time_end.")
            return

        raise PricingError(f"Unknown rule_type: {rule_type}")
