"""
QuoteService — Module 11 foundation.

Computes a deterministic price quote: resolve exactly one base rule (most
specific match), compose all matching modifier rules (surcharges/
adjustments) in priority order, then apply matching promotions in priority
order (stackable ones combine; a non-stackable one is exclusive). Every
amount is Decimal, quantized to 2 places with ROUND_HALF_UP at each step —
no floating-point arithmetic anywhere.

Standalone by design: does not touch Booking, Finance, Invoice, Wallet, or
Matching. Callers (a future module) decide when/whether to request a quote.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import (
    DEFAULT_CURRENCY,
    PricingRule,
    PricingRuleType,
    Promotion,
    PromotionConditionType,
    PromotionEffectType,
    Quote,
    QuoteLine,
    QuoteLineType,
    QuoteStatus,
)
from .configuration import PricingConfiguration
from .errors import PricingError

QUANT = Decimal("0.01")


def _q(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)


class QuoteService:
    """Generates deterministic Quote + QuoteLine breakdowns."""

    @classmethod
    @transaction.atomic
    def generate_quote(
        cls,
        *,
        tenant_id,
        service_category=None,
        supplier=None,
        order=None,
        base_amount=None,
        duration_hours=None,
        requested_at=None,
        is_holiday=False,
        customer_profile=None,
        currency=None,
        expires_at=None,
        metadata=None,
    ) -> Quote:
        requested_at = requested_at or timezone.now()
        if timezone.is_naive(requested_at):
            raise PricingError("requested_at must be timezone-aware.")

        resolved_currency = currency or DEFAULT_CURRENCY

        resolved_base, base_rule = cls._resolve_base_amount(
            tenant_id=tenant_id, service_category=service_category, supplier=supplier,
            explicit_base_amount=base_amount, duration_hours=duration_hours,
        )

        quote = Quote.objects.create(
            tenant_id=tenant_id,
            order=order,
            service_category=service_category,
            supplier=supplier,
            status=QuoteStatus.ACTIVE,
            currency=resolved_currency,
            base_amount=resolved_base,
            requested_at=requested_at,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        sequence = 0
        lines = [QuoteLine(
            tenant_id=tenant_id, quote=quote, line_type=QuoteLineType.BASE,
            description="Base price", amount=resolved_base, sequence=sequence,
        )]

        running_total = resolved_base
        for rule in cls._matching_modifier_rules(
            tenant_id=tenant_id, service_category=service_category, supplier=supplier,
            requested_at=requested_at, is_holiday=is_holiday,
        ):
            sequence += 1
            delta = cls._modifier_delta(rule, running_total)
            running_total = _q(running_total + delta)
            lines.append(QuoteLine(
                tenant_id=tenant_id, quote=quote, line_type=QuoteLineType.PRICING_RULE,
                source_rule=rule, description=rule.name, amount=delta, sequence=sequence,
            ))

        subtotal = running_total

        for promotion in cls._matching_promotions(
            tenant_id=tenant_id, service_category=service_category, supplier=supplier,
            subtotal=subtotal, order=order, customer_profile=customer_profile, requested_at=requested_at,
        ):
            applied_any = False
            for effect in promotion.effects.all():
                delta = cls._effect_delta(effect, running_total)
                if delta == 0:
                    continue
                sequence += 1
                running_total = _q(running_total + delta)
                lines.append(QuoteLine(
                    tenant_id=tenant_id, quote=quote, line_type=QuoteLineType.PROMOTION,
                    source_promotion=promotion, description=promotion.name, amount=delta, sequence=sequence,
                ))
                applied_any = True
            if applied_any and not promotion.stackable:
                break

        QuoteLine.objects.bulk_create(lines)

        total = running_total
        quote.subtotal_amount = subtotal
        quote.surcharge_amount = _q(subtotal - resolved_base)
        quote.discount_amount = _q(subtotal - total)
        quote.total_amount = total
        quote.pricing_snapshot = {
            "base_amount": str(resolved_base),
            "base_rule_id": str(base_rule.id) if base_rule else None,
            "lines": [
                {
                    "type": line.line_type,
                    "description": line.description,
                    "amount": str(line.amount),
                    "sequence": line.sequence,
                }
                for line in lines
            ],
            "subtotal_amount": str(subtotal),
            "surcharge_amount": str(quote.surcharge_amount),
            "discount_amount": str(quote.discount_amount),
            "total_amount": str(total),
            "computed_at": timezone.now().isoformat(),
        }
        quote.save(update_fields=[
            "subtotal_amount", "surcharge_amount", "discount_amount", "total_amount",
            "pricing_snapshot", "updated_at",
        ])

        return quote

    # --- base price resolution ---------------------------------------------

    @classmethod
    def _resolve_base_amount(cls, *, tenant_id, service_category, supplier, explicit_base_amount, duration_hours):
        if explicit_base_amount is not None:
            return _q(explicit_base_amount), None

        rule = cls._select_base_rule(tenant_id=tenant_id, service_category=service_category, supplier=supplier)
        if rule is None:
            raise PricingError("No base pricing rule configured and no explicit base_amount provided.")

        if rule.rule_type == PricingRuleType.FIXED_AMOUNT:
            return _q(rule.amount), rule

        # HOURLY_RATE
        if duration_hours is None:
            raise PricingError("HOURLY_RATE base rule requires duration_hours.")
        return _q(rule.amount * Decimal(str(duration_hours))), rule

    @staticmethod
    def _select_base_rule(*, tenant_id, service_category, supplier):
        from ..models import BASE_RULE_TYPES

        candidates = list(
            PricingRule.objects.filter(
                tenant_id=tenant_id, is_active=True, rule_type__in=BASE_RULE_TYPES,
            ).filter(
                Q(service_category__isnull=True) | Q(service_category=service_category),
            ).filter(
                Q(supplier__isnull=True) | Q(supplier=supplier),
            ),
        )
        if not candidates:
            return None

        def specificity_key(rule):
            supplier_specific = 0 if rule.supplier_id is not None else 1
            category_specific = 0 if rule.service_category_id is not None else 1
            return (supplier_specific, category_specific, rule.priority, rule.created_at, rule.id)

        candidates.sort(key=specificity_key)
        return candidates[0]

    # --- modifier rules (surcharges/adjustments) ----------------------------

    @classmethod
    def _matching_modifier_rules(cls, *, tenant_id, service_category, supplier, requested_at, is_holiday):
        from ..models import MODIFIER_RULE_TYPES

        qs = PricingRule.objects.filter(
            tenant_id=tenant_id, is_active=True, rule_type__in=MODIFIER_RULE_TYPES,
        ).filter(
            Q(service_category__isnull=True) | Q(service_category=service_category),
        ).filter(
            Q(supplier__isnull=True) | Q(supplier=supplier),
        ).order_by("priority", "created_at", "id")

        local_dt = timezone.localtime(requested_at)
        weekend_days = PricingConfiguration.get_weekend_days(tenant_id=tenant_id)

        matched = []
        for rule in qs:
            if rule.rule_type == PricingRuleType.TIME_OF_DAY_SURCHARGE:
                if not (rule.time_start <= local_dt.time() < rule.time_end):
                    continue
            elif rule.rule_type == PricingRuleType.WEEKEND_SURCHARGE:
                if local_dt.weekday() not in weekend_days:
                    continue
            elif rule.rule_type == PricingRuleType.HOLIDAY_SURCHARGE:
                if not is_holiday:
                    continue
            matched.append(rule)
        return matched

    @staticmethod
    def _modifier_delta(rule, running_total) -> Decimal:
        if rule.rule_type == PricingRuleType.PERCENTAGE_ADJUSTMENT:
            return _q(running_total * rule.percentage / Decimal("100"))
        if rule.amount is not None:
            return _q(rule.amount)
        return _q(running_total * rule.percentage / Decimal("100"))

    # --- promotions ----------------------------------------------------------

    @classmethod
    def _matching_promotions(cls, *, tenant_id, service_category, supplier, subtotal, order, customer_profile, requested_at):
        qs = Promotion.objects.filter(
            tenant_id=tenant_id, is_active=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=requested_at),
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=requested_at),
        ).prefetch_related("conditions", "effects").order_by("priority", "created_at", "id")

        matched = []
        for promotion in qs:
            if cls._promotion_conditions_met(
                promotion, tenant_id=tenant_id, service_category=service_category, supplier=supplier,
                subtotal=subtotal, order=order, customer_profile=customer_profile,
            ):
                matched.append(promotion)
        return matched

    @staticmethod
    def _promotion_conditions_met(promotion, *, tenant_id, service_category, supplier, subtotal, order, customer_profile) -> bool:
        for condition in promotion.conditions.all():
            if condition.condition_type == PromotionConditionType.SERVICE_CATEGORY:
                if service_category is None or condition.service_category_id != service_category.id:
                    return False

            elif condition.condition_type == PromotionConditionType.SUPPLIER:
                if supplier is None or condition.supplier_id != supplier.id:
                    return False

            elif condition.condition_type == PromotionConditionType.MIN_AMOUNT:
                if subtotal < condition.min_amount:
                    return False

            elif condition.condition_type == PromotionConditionType.FIRST_ORDER_ONLY:
                resolved_customer = customer_profile
                if resolved_customer is None and order is not None and order.customer_profile_id:
                    resolved_customer = order.customer_profile
                if resolved_customer is None:
                    return False

                from apps.orders.models import Order as OrderModel

                other_orders = OrderModel.objects.filter(tenant_id=tenant_id, customer_profile=resolved_customer)
                if order is not None:
                    other_orders = other_orders.exclude(id=order.id)
                if other_orders.exists():
                    return False

        return True

    @staticmethod
    def _effect_delta(effect, running_total) -> Decimal:
        if effect.effect_type == PromotionEffectType.FIXED_DISCOUNT:
            raw = effect.fixed_amount
        else:
            raw = running_total * effect.percentage / Decimal("100")

        if effect.max_discount_amount is not None:
            raw = min(raw, effect.max_discount_amount)
        raw = min(raw, running_total)
        return _q(-raw)
