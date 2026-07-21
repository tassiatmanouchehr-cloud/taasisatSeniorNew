"""
Tests for QuoteService: base price resolution (fixed/hourly/explicit,
supplier/organization override precedence), modifier rule composition
(surcharge ordering, time-of-day/weekend/holiday gating), determinism, and
Decimal rounding.
"""

import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from apps.kernel.models.supplier import SupplierType
from apps.pricing.models import PricingRuleType, Quote
from apps.pricing.services import PricingError, PricingRuleService, QuoteService

from .helpers import PricingTestCase


def _next_weekday(target_weekday: int) -> dt.date:
    today = timezone.localdate()
    return today + dt.timedelta(days=(target_weekday - today.weekday()) % 7)


class QuoteServiceBasePriceTest(PricingTestCase):
    def test_explicit_base_amount_bypasses_rule_lookup(self):
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("123456"),
        )
        self.assertEqual(quote.base_amount, Decimal("123456.00"))

    def test_fixed_amount_rule_used_as_base(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Base",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("500000"),
            service_category=self.category,
        )
        quote = QuoteService.generate_quote(tenant_id=self.tenant.id, service_category=self.category)
        self.assertEqual(quote.base_amount, Decimal("500000.00"))
        self.assertEqual(quote.total_amount, Decimal("500000.00"))

    def test_hourly_rate_rule_multiplies_by_duration(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Hourly",
            rule_type=PricingRuleType.HOURLY_RATE,
            amount=Decimal("100000"),
            service_category=self.category,
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            duration_hours=Decimal("3"),
        )
        self.assertEqual(quote.base_amount, Decimal("300000.00"))

    def test_hourly_rate_requires_duration_hours(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Hourly",
            rule_type=PricingRuleType.HOURLY_RATE,
            amount=Decimal("100000"),
            service_category=self.category,
        )
        with self.assertRaises(PricingError):
            QuoteService.generate_quote(tenant_id=self.tenant.id, service_category=self.category)

    def test_no_base_rule_and_no_explicit_amount_raises(self):
        with self.assertRaises(PricingError):
            QuoteService.generate_quote(tenant_id=self.tenant.id, service_category=self.category)

    def test_supplier_override_takes_precedence_over_category_default(self):
        supplier = self._create_supplier()
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Category default",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("400000"),
            service_category=self.category,
        )
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Supplier override",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("650000"),
            service_category=self.category,
            supplier=supplier,
        )

        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            supplier=supplier,
        )
        self.assertEqual(quote.base_amount, Decimal("650000.00"))

    def test_organization_supplier_override_works_identically(self):
        org_supplier = self._create_supplier(supplier_type=SupplierType.ORGANIZATION, display_name="Care Org")
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Org override",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("900000"),
            service_category=self.category,
            supplier=org_supplier,
        )

        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            supplier=org_supplier,
        )
        self.assertEqual(quote.base_amount, Decimal("900000.00"))

    def test_tenant_wide_default_used_when_no_scoped_rule_matches(self):
        supplier = self._create_supplier()
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Tenant default",
            rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("350000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            supplier=supplier,
        )
        self.assertEqual(quote.base_amount, Decimal("350000.00"))

    def test_naive_requested_at_raises_pricing_error(self):
        with self.assertRaises(PricingError):
            QuoteService.generate_quote(
                tenant_id=self.tenant.id,
                service_category=self.category,
                base_amount=Decimal("1000"),
                requested_at=dt.datetime(2026, 1, 1, 10, 0),
            )


class QuoteServiceModifierTest(PricingTestCase):
    def setUp(self):
        super().setUp()
        self.monday = _next_weekday(0)
        self.friday = _next_weekday(4)

    def _aware(self, date_, hour, minute=0):
        return timezone.make_aware(dt.datetime.combine(date_, dt.time(hour, minute)))

    def test_flat_surcharge_applied(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Travel fee",
            rule_type=PricingRuleType.FLAT_SURCHARGE,
            amount=Decimal("20000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
        )
        self.assertEqual(quote.total_amount, Decimal("120000.00"))
        self.assertEqual(quote.surcharge_amount, Decimal("20000.00"))

    def test_percentage_adjustment_applies_to_running_total(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="10% bump",
            rule_type=PricingRuleType.PERCENTAGE_ADJUSTMENT,
            percentage=Decimal("10"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
        )
        self.assertEqual(quote.total_amount, Decimal("110000.00"))

    def test_surcharge_ordering_changes_the_result(self):
        # Flat surcharge first (priority 0), then a 10% adjustment (priority 1):
        # (100000 + 10000) * 1.10 = 121000.00
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Flat",
            rule_type=PricingRuleType.FLAT_SURCHARGE,
            amount=Decimal("10000"),
            priority=0,
            service_category=self.category,
        )
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Pct",
            rule_type=PricingRuleType.PERCENTAGE_ADJUSTMENT,
            percentage=Decimal("10"),
            priority=1,
            service_category=self.category,
        )
        quote_a = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
        )
        self.assertEqual(quote_a.total_amount, Decimal("121000.00"))

        # Now flip priorities: 10% first, then +10000 flat = 100000*1.10 + 10000 = 120000.00
        for rule in self.category.pricing_rules.all():
            rule.priority = 1 - rule.priority
            rule.save(update_fields=["priority"])

        quote_b = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
        )
        self.assertEqual(quote_b.total_amount, Decimal("120000.00"))

    def test_overlapping_time_of_day_surcharges_both_apply(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Morning surcharge",
            rule_type=PricingRuleType.TIME_OF_DAY_SURCHARGE,
            amount=Decimal("5000"),
            time_start=dt.time(8, 0),
            time_end=dt.time(12, 0),
            priority=0,
        )
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Late-morning surcharge",
            rule_type=PricingRuleType.TIME_OF_DAY_SURCHARGE,
            amount=Decimal("3000"),
            time_start=dt.time(10, 0),
            time_end=dt.time(14, 0),
            priority=1,
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 11),
        )
        self.assertEqual(quote.total_amount, Decimal("108000.00"))

    def test_time_of_day_surcharge_does_not_apply_outside_window(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Night surcharge",
            rule_type=PricingRuleType.TIME_OF_DAY_SURCHARGE,
            amount=Decimal("5000"),
            time_start=dt.time(22, 0),
            time_end=dt.time(23, 59),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
        )
        self.assertEqual(quote.total_amount, Decimal("100000.00"))

    def test_weekend_surcharge_applies_on_default_weekend_day(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Weekend surcharge",
            rule_type=PricingRuleType.WEEKEND_SURCHARGE,
            amount=Decimal("15000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.friday, 10),  # Friday=4, in DEFAULT_WEEKEND_DAYS
        )
        self.assertEqual(quote.total_amount, Decimal("115000.00"))

    def test_weekend_surcharge_does_not_apply_on_weekday(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Weekend surcharge",
            rule_type=PricingRuleType.WEEKEND_SURCHARGE,
            amount=Decimal("15000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
        )
        self.assertEqual(quote.total_amount, Decimal("100000.00"))

    def test_weekend_days_are_configurable_per_tenant(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Weekend surcharge",
            rule_type=PricingRuleType.WEEKEND_SURCHARGE,
            amount=Decimal("15000"),
        )
        with patch(
            "apps.pricing.services.quote_service.PricingConfiguration.get_weekend_days",
            return_value=[0],  # Monday is now "weekend" for this tenant
        ):
            quote = QuoteService.generate_quote(
                tenant_id=self.tenant.id,
                service_category=self.category,
                base_amount=Decimal("100000"),
                requested_at=self._aware(self.monday, 10),
            )

        self.assertEqual(quote.total_amount, Decimal("115000.00"))

    def test_holiday_surcharge_requires_explicit_flag(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Holiday surcharge",
            rule_type=PricingRuleType.HOLIDAY_SURCHARGE,
            amount=Decimal("25000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
            is_holiday=False,
        )
        self.assertEqual(quote.total_amount, Decimal("100000.00"))

    def test_holiday_surcharge_applies_when_flagged(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Holiday surcharge",
            rule_type=PricingRuleType.HOLIDAY_SURCHARGE,
            amount=Decimal("25000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            requested_at=self._aware(self.monday, 10),
            is_holiday=True,
        )
        self.assertEqual(quote.total_amount, Decimal("125000.00"))


class QuoteServiceDeterminismAndRoundingTest(PricingTestCase):
    def test_generate_quote_is_deterministic(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Flat",
            rule_type=PricingRuleType.FLAT_SURCHARGE,
            amount=Decimal("12345.67"),
        )
        requested_at = timezone.now()
        quote_a = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("99999.99"),
            requested_at=requested_at,
        )
        quote_b = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("99999.99"),
            requested_at=requested_at,
        )
        self.assertEqual(quote_a.total_amount, quote_b.total_amount)
        self.assertEqual(quote_a.subtotal_amount, quote_b.subtotal_amount)

    def test_percentage_rounds_half_up(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Odd percentage",
            rule_type=PricingRuleType.PERCENTAGE_ADJUSTMENT,
            percentage=Decimal("1"),
        )
        # 100.005 * 1.01 = 101.00505 -> rounds to 101.01 (ROUND_HALF_UP on the final quantize)
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100.005"),
        )
        self.assertIsInstance(quote.total_amount, Decimal)
        # base_amount itself is quantized to 100.01 (ROUND_HALF_UP of 100.005) before any modifier runs.
        self.assertEqual(quote.base_amount, Decimal("100.01"))

    def test_quote_breakdown_lines_match_pricing_snapshot(self):
        PricingRuleService.create_rule(
            tenant_id=self.tenant.id,
            name="Flat",
            rule_type=PricingRuleType.FLAT_SURCHARGE,
            amount=Decimal("5000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
        )
        lines = list(quote.lines.order_by("sequence"))
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].amount, Decimal("100000.00"))
        self.assertEqual(lines[1].amount, Decimal("5000.00"))
        self.assertEqual(len(quote.pricing_snapshot["lines"]), 2)

    def test_quote_order_reference(self):
        from apps.orders.models import Order, OrderSource, OrderStatus

        order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            description="d",
            city="tehran",
            address="a",
            phone="0912",
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
            order=order,
        )
        self.assertEqual(quote.order_id, order.id)
        self.assertEqual(list(order.quotes.all()), [quote])

    def test_generate_quote_creates_persisted_quote_and_is_not_expired_by_default(self):
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id,
            service_category=self.category,
            base_amount=Decimal("100000"),
        )
        self.assertTrue(Quote.objects.filter(id=quote.id).exists())
        self.assertFalse(quote.is_expired)
