"""Tests for PricingRuleService: creation validation, updates, deactivation."""

import datetime as dt
from decimal import Decimal

from apps.pricing.models import PricingRule, PricingRuleType
from apps.pricing.services import PricingError, PricingRuleService

from .helpers import PricingTestCase


class PricingRuleServiceTest(PricingTestCase):
    def test_create_fixed_amount_rule(self):
        rule = PricingRuleService.create_rule(
            tenant_id=self.tenant.id, name="Base rate", rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("500000"),
        )
        self.assertEqual(rule.amount, Decimal("500000"))

    def test_fixed_amount_requires_amount(self):
        with self.assertRaises(PricingError):
            PricingRuleService.create_rule(
                tenant_id=self.tenant.id, name="Bad", rule_type=PricingRuleType.FIXED_AMOUNT,
            )

    def test_fixed_amount_rejects_negative_amount(self):
        with self.assertRaises(PricingError):
            PricingRuleService.create_rule(
                tenant_id=self.tenant.id, name="Bad", rule_type=PricingRuleType.FIXED_AMOUNT, amount=Decimal("-1"),
            )

    def test_percentage_adjustment_requires_percentage(self):
        with self.assertRaises(PricingError):
            PricingRuleService.create_rule(
                tenant_id=self.tenant.id, name="Bad", rule_type=PricingRuleType.PERCENTAGE_ADJUSTMENT,
            )

    def test_time_of_day_surcharge_requires_time_bounds(self):
        with self.assertRaises(PricingError):
            PricingRuleService.create_rule(
                tenant_id=self.tenant.id, name="Night surcharge", rule_type=PricingRuleType.TIME_OF_DAY_SURCHARGE,
                amount=Decimal("50000"),
            )

    def test_time_of_day_surcharge_rejects_start_after_end(self):
        with self.assertRaises(PricingError):
            PricingRuleService.create_rule(
                tenant_id=self.tenant.id, name="Night surcharge", rule_type=PricingRuleType.TIME_OF_DAY_SURCHARGE,
                amount=Decimal("50000"), time_start=dt.time(22, 0), time_end=dt.time(6, 0),
            )

    def test_time_of_day_surcharge_requires_amount_or_percentage(self):
        with self.assertRaises(PricingError):
            PricingRuleService.create_rule(
                tenant_id=self.tenant.id, name="Night surcharge", rule_type=PricingRuleType.TIME_OF_DAY_SURCHARGE,
                time_start=dt.time(22, 0), time_end=dt.time(23, 59),
            )

    def test_create_time_of_day_surcharge_succeeds(self):
        rule = PricingRuleService.create_rule(
            tenant_id=self.tenant.id, name="Night surcharge", rule_type=PricingRuleType.TIME_OF_DAY_SURCHARGE,
            amount=Decimal("50000"), time_start=dt.time(22, 0), time_end=dt.time(23, 59),
        )
        self.assertEqual(rule.time_start, dt.time(22, 0))

    def test_unknown_rule_type_rejected(self):
        with self.assertRaises(PricingError):
            PricingRuleService.create_rule(
                tenant_id=self.tenant.id, name="Bad", rule_type="NOT_A_REAL_TYPE", amount=Decimal("1"),
            )

    def test_update_rule_revalidates(self):
        rule = PricingRuleService.create_rule(
            tenant_id=self.tenant.id, name="Base rate", rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("500000"),
        )
        with self.assertRaises(PricingError):
            PricingRuleService.update_rule(rule_id=rule.id, amount=Decimal("-5"))

    def test_update_rule_applies_valid_change(self):
        rule = PricingRuleService.create_rule(
            tenant_id=self.tenant.id, name="Base rate", rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("500000"),
        )
        updated = PricingRuleService.update_rule(rule_id=rule.id, amount=Decimal("600000"))
        self.assertEqual(updated.amount, Decimal("600000"))

    def test_deactivate_rule(self):
        rule = PricingRuleService.create_rule(
            tenant_id=self.tenant.id, name="Base rate", rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("500000"),
        )
        PricingRuleService.deactivate_rule(rule_id=rule.id)
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)

    def test_rule_scoped_to_supplier_and_category(self):
        supplier = self._create_supplier()
        rule = PricingRuleService.create_rule(
            tenant_id=self.tenant.id, name="Supplier override", rule_type=PricingRuleType.FIXED_AMOUNT,
            amount=Decimal("700000"), service_category=self.category, supplier=supplier,
        )
        self.assertEqual(PricingRule.objects.filter(supplier=supplier, service_category=self.category).count(), 1)
        self.assertEqual(rule.tenant_id, self.tenant.id)
