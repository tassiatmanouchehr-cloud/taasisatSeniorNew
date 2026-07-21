"""
Pricing Rules, Quotes & Promotions — Module 11 foundation.

Standalone pricing domain: computes deterministic quotes from composable
PricingRule rows plus Promotion effects. Deliberately does not import from
apps.finance — MONEY_MAX_DIGITS/MONEY_DECIMAL_PLACES/DEFAULT_CURRENCY below
intentionally mirror Finance's money precision (apps/finance/models/document.py)
for consistency across the platform, but are defined locally so Pricing has
no cross-domain dependency in either direction. Finance is logically
downstream of Pricing (a future invoice would consume a Quote), not the
reverse.

Every model keys off apps.kernel.models.supplier.ServiceSupplier for
supplier/organization scoping (never CaregiverProfile/OrganizationProfile
directly) — an "organization-specific override" is simply a PricingRule or
PromotionCondition scoped to a SupplierType.ORGANIZATION supplier, the same
unification principle established in Module 10's CapacityRule.
"""

import uuid
from decimal import Decimal

from django.db import models

from apps.common.managers import TenantScopedManager

MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2
DEFAULT_CURRENCY = "IRR"


class PricingRuleType(models.TextChoices):
    """
    A discriminator, not a separate model/table — mirrors how EligibilityCode,
    PaymentMethod, etc. are modeled elsewhere in this codebase.
    """

    FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed Amount"
    HOURLY_RATE = "HOURLY_RATE", "Hourly Rate"
    PERCENTAGE_ADJUSTMENT = "PERCENTAGE_ADJUSTMENT", "Percentage Adjustment"
    FLAT_SURCHARGE = "FLAT_SURCHARGE", "Flat Surcharge"
    TIME_OF_DAY_SURCHARGE = "TIME_OF_DAY_SURCHARGE", "Time-of-Day Surcharge"
    WEEKEND_SURCHARGE = "WEEKEND_SURCHARGE", "Weekend Surcharge"
    HOLIDAY_SURCHARGE = "HOLIDAY_SURCHARGE", "Holiday Surcharge"


# Exactly one BASE_RULE_TYPES rule is selected per quote (most specific match).
# All MODIFIER_RULE_TYPES rules that match compose together, in priority order.
BASE_RULE_TYPES = (PricingRuleType.FIXED_AMOUNT, PricingRuleType.HOURLY_RATE)
MODIFIER_RULE_TYPES = (
    PricingRuleType.PERCENTAGE_ADJUSTMENT,
    PricingRuleType.FLAT_SURCHARGE,
    PricingRuleType.TIME_OF_DAY_SURCHARGE,
    PricingRuleType.WEEKEND_SURCHARGE,
    PricingRuleType.HOLIDAY_SURCHARGE,
)


class PricingRule(models.Model):
    """One composable pricing rule: a base price or a surcharge/adjustment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="pricing_rules",
    )

    name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=30, choices=PricingRuleType.choices, db_index=True)

    # Scope: null means "applies to all". Both may be set for the most
    # specific override (e.g. one supplier's rate for one category).
    service_category = models.ForeignKey(
        "orders.ServiceCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pricing_rules",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pricing_rules",
    )

    amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    percentage = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)

    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)

    priority = models.IntegerField(default=0, help_text="Lower runs first. Ties broken by created_at, then id.")
    is_active = models.BooleanField(default=True)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "pricing_rule"
        ordering = ["priority", "created_at"]
        indexes = [
            models.Index(fields=["tenant", "rule_type", "is_active"], name="idx_pricerule_tenant_type_st"),
        ]

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class QuoteStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"


class Quote(models.Model):
    """
    A deterministic, persisted pricing computation. Quote.order is the
    approved integration point for Orders — nullable, SET_NULL — rather
    than adding a field to the Order model itself.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="quotes",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
    )
    service_category = models.ForeignKey(
        "orders.ServiceCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
    )

    status = models.CharField(max_length=20, choices=QuoteStatus.choices, default=QuoteStatus.ACTIVE, db_index=True)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)

    base_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0")
    )
    surcharge_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0")
    )
    discount_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0")
    )
    subtotal_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0")
    )
    total_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0")
    )

    requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The point in time pricing was evaluated against (time-of-day/weekend/holiday rules).",
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    pricing_snapshot = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "pricing_quote"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "order"], name="idx_quote_tenant_order"),
        ]

    def __str__(self):
        return f"Quote {self.id} [{self.status}] {self.total_amount} {self.currency}"

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        from django.utils import timezone

        return timezone.now() >= self.expires_at


class QuoteLineType(models.TextChoices):
    BASE = "BASE", "Base"
    PRICING_RULE = "PRICING_RULE", "Pricing Rule"
    PROMOTION = "PROMOTION", "Promotion"


class QuoteLine(models.Model):
    """One signed line in a Quote's breakdown. Positive = adds, negative = discounts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="quote_lines",
    )
    quote = models.ForeignKey(
        "pricing.Quote",
        on_delete=models.CASCADE,
        related_name="lines",
    )

    line_type = models.CharField(max_length=20, choices=QuoteLineType.choices)
    source_rule = models.ForeignKey(
        "pricing.PricingRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quote_lines",
    )
    source_promotion = models.ForeignKey(
        "pricing.Promotion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quote_lines",
    )

    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    sequence = models.IntegerField()
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "pricing_quote_line"
        ordering = ["sequence"]

    def __str__(self):
        return f"QuoteLine({self.line_type}, {self.amount}) seq={self.sequence}"


class Promotion(models.Model):
    """A named, tenant-scoped promotional campaign. Conditions gate it; effects define its discount."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="promotions",
    )

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    stackable = models.BooleanField(
        default=False,
        help_text="If False, applying this promotion stops any further (lower-priority) promotions from applying.",
    )
    priority = models.IntegerField(default=0, help_text="Lower runs first. Ties broken by created_at, then id.")

    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "pricing_promotion"
        ordering = ["priority", "created_at"]

    def __str__(self):
        return f"{self.name} [{'active' if self.is_active else 'inactive'}]"


class PromotionConditionType(models.TextChoices):
    FIRST_ORDER_ONLY = "FIRST_ORDER_ONLY", "First Order Only"
    SERVICE_CATEGORY = "SERVICE_CATEGORY", "Service Category"
    SUPPLIER = "SUPPLIER", "Supplier"
    MIN_AMOUNT = "MIN_AMOUNT", "Minimum Amount"


class PromotionCondition(models.Model):
    """One condition that must hold for its Promotion to apply. No conditions = applies tenant-wide."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="promotion_conditions",
    )
    promotion = models.ForeignKey(
        "pricing.Promotion",
        on_delete=models.CASCADE,
        related_name="conditions",
    )

    condition_type = models.CharField(max_length=30, choices=PromotionConditionType.choices)
    service_category = models.ForeignKey(
        "orders.ServiceCategory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
    )
    min_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "pricing_promotion_condition"

    def __str__(self):
        return f"{self.condition_type} (promotion={self.promotion_id})"


class PromotionEffectType(models.TextChoices):
    PERCENTAGE_DISCOUNT = "PERCENTAGE_DISCOUNT", "Percentage Discount"
    FIXED_DISCOUNT = "FIXED_DISCOUNT", "Fixed Discount"


class PromotionEffect(models.Model):
    """What a Promotion does once its conditions are met."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="promotion_effects",
    )
    promotion = models.ForeignKey(
        "pricing.Promotion",
        on_delete=models.CASCADE,
        related_name="effects",
    )

    effect_type = models.CharField(max_length=30, choices=PromotionEffectType.choices)
    percentage = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    fixed_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    max_discount_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "pricing_promotion_effect"

    def __str__(self):
        return f"{self.effect_type} (promotion={self.promotion_id})"
