"""Tests for QuoteService's promotion application: effects, conditions, and ordering."""

from decimal import Decimal

from apps.orders.models import OrderSource, OrderStatus
from apps.pricing.models import PromotionConditionType, PromotionEffectType
from apps.pricing.services import PromotionService, QuoteService

from .helpers import PricingTestCase


class QuoteServicePromotionTest(PricingTestCase):
    def test_percentage_discount_applied(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="10% off")
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.PERCENTAGE_DISCOUNT, percentage=Decimal("10"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.total_amount, Decimal("90000.00"))
        self.assertEqual(quote.discount_amount, Decimal("10000.00"))

    def test_fixed_discount_applied(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Flat off")
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("15000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.total_amount, Decimal("85000.00"))

    def test_percentage_discount_capped_by_max_discount_amount(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Capped")
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.PERCENTAGE_DISCOUNT,
            percentage=Decimal("50"), max_discount_amount=Decimal("20000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.discount_amount, Decimal("20000.00"))
        self.assertEqual(quote.total_amount, Decimal("80000.00"))

    def test_discount_never_pushes_total_below_zero(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Huge discount")
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("999999"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.total_amount, Decimal("0.00"))

    def test_min_amount_condition_blocks_promotion_below_threshold(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Bulk discount")
        PromotionService.add_condition(
            promotion=promotion, condition_type=PromotionConditionType.MIN_AMOUNT, min_amount=Decimal("200000"),
        )
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.total_amount, Decimal("100000.00"))

    def test_min_amount_condition_allows_promotion_above_threshold(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Bulk discount")
        PromotionService.add_condition(
            promotion=promotion, condition_type=PromotionConditionType.MIN_AMOUNT, min_amount=Decimal("50000"),
        )
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )
        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.total_amount, Decimal("90000.00"))

    def test_service_category_condition_scopes_promotion(self):
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Category-only")
        PromotionService.add_condition(
            promotion=promotion, condition_type=PromotionConditionType.SERVICE_CATEGORY,
            service_category=self.category,
        )
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )

        matching_quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(matching_quote.total_amount, Decimal("90000.00"))

        other_quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.other_category, base_amount=Decimal("100000"),
        )
        self.assertEqual(other_quote.total_amount, Decimal("100000.00"))

    def test_supplier_condition_scopes_promotion(self):
        supplier = self._create_supplier()
        other_supplier = self._create_supplier(display_name="Someone Else")
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Supplier-only")
        PromotionService.add_condition(
            promotion=promotion, condition_type=PromotionConditionType.SUPPLIER, supplier=supplier,
        )
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )

        matching_quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, supplier=supplier, base_amount=Decimal("100000"),
        )
        self.assertEqual(matching_quote.total_amount, Decimal("90000.00"))

        other_quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, supplier=other_supplier,
            base_amount=Decimal("100000"),
        )
        self.assertEqual(other_quote.total_amount, Decimal("100000.00"))

    def _create_customer(self):
        from apps.accounts.models.profiles import CustomerProfile
        from apps.kernel.models import Person, UserAccount
        import uuid

        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Test Customer")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name="Test Customer")

    def _make_order(self, customer_profile):
        from apps.orders.models import Order

        return Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="d", city="tehran", address="a", phone="0912",
            customer_profile=customer_profile,
        )

    def test_first_order_only_condition_allows_new_customer(self):
        customer = self._create_customer()
        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Welcome")
        PromotionService.add_condition(promotion=promotion, condition_type=PromotionConditionType.FIRST_ORDER_ONLY)
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )

        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
            customer_profile=customer,
        )
        self.assertEqual(quote.total_amount, Decimal("90000.00"))

    def test_first_order_only_condition_blocks_repeat_customer(self):
        customer = self._create_customer()
        self._make_order(customer)  # a prior order already exists

        promotion = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Welcome")
        PromotionService.add_condition(promotion=promotion, condition_type=PromotionConditionType.FIRST_ORDER_ONLY)
        PromotionService.add_effect(
            promotion=promotion, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )

        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
            customer_profile=customer,
        )
        self.assertEqual(quote.total_amount, Decimal("100000.00"))

    def test_non_stackable_promotion_is_exclusive(self):
        # Higher-priority (lower number) non-stackable promotion applies; the
        # lower-priority one must NOT also apply.
        first = PromotionService.create_promotion(tenant_id=self.tenant.id, name="First", priority=0, stackable=False)
        PromotionService.add_effect(
            promotion=first, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )
        second = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Second", priority=1, stackable=False)
        PromotionService.add_effect(
            promotion=second, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("5000"),
        )

        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.discount_amount, Decimal("10000.00"))

    def test_stackable_promotions_combine(self):
        first = PromotionService.create_promotion(tenant_id=self.tenant.id, name="First", priority=0, stackable=True)
        PromotionService.add_effect(
            promotion=first, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("10000"),
        )
        second = PromotionService.create_promotion(tenant_id=self.tenant.id, name="Second", priority=1, stackable=True)
        PromotionService.add_effect(
            promotion=second, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("5000"),
        )

        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        self.assertEqual(quote.discount_amount, Decimal("15000.00"))

    def test_promotion_ordering_stackable_then_nonstackable_stops_afterward(self):
        stackable_first = PromotionService.create_promotion(
            tenant_id=self.tenant.id, name="Stackable", priority=0, stackable=True,
        )
        PromotionService.add_effect(
            promotion=stackable_first, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("5000"),
        )
        exclusive_second = PromotionService.create_promotion(
            tenant_id=self.tenant.id, name="Exclusive", priority=1, stackable=False,
        )
        PromotionService.add_effect(
            promotion=exclusive_second, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("7000"),
        )
        blocked_third = PromotionService.create_promotion(
            tenant_id=self.tenant.id, name="Blocked", priority=2, stackable=True,
        )
        PromotionService.add_effect(
            promotion=blocked_third, effect_type=PromotionEffectType.FIXED_DISCOUNT, fixed_amount=Decimal("3000"),
        )

        quote = QuoteService.generate_quote(
            tenant_id=self.tenant.id, service_category=self.category, base_amount=Decimal("100000"),
        )
        # 5000 (stackable) + 7000 (exclusive, then stop) — the 3000 promotion never applies.
        self.assertEqual(quote.discount_amount, Decimal("12000.00"))
