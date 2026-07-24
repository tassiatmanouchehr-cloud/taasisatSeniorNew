"""
Tests for Phase 6.2A — Marketplace Price Authority Remediation.

Proves that PreServicePaymentService._resolve_amount_irr() uses the
accepted OrderOffer.price_amount for marketplace orders, and that
non-marketplace orders continue to use the pricing engine (Quote).
"""

import uuid
from decimal import Decimal

from django.test import TestCase

from apps.commission.services.errors import PreServicePaymentError
from apps.commission.services.preservice_payment_service import PreServicePaymentService
from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import (
    CatalogStatus,
    Order,
    OrderOffer,
    OrderOfferStatus,
    OrderSource,
    OrderStatus,
    ServiceCategory,
)


def _make_tenant():
    return Tenant.objects.create(slug=f"price-auth-{uuid.uuid4().hex[:8]}", name="Price Auth Test")


def _make_supplier(tenant):
    return ServiceSupplier.objects.create(
        tenant=tenant,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        linked_entity_id=uuid.uuid4(),
        linked_entity_type="TestProfile",
        display_name="Test Supplier",
        status=SupplierStatus.ACTIVE,
        availability_status=AvailabilityStatus.AVAILABLE,
        verification_level=VerificationLevel.BASIC,
    )


def _make_order(tenant, *, status=OrderStatus.WAITING_SERVICE):
    category = ServiceCategory.objects.create(
        tenant=tenant, name="Care", slug=f"care-{uuid.uuid4().hex[:6]}", status=CatalogStatus.ACTIVE
    )
    return Order.objects.create(
        tenant=tenant,
        source=OrderSource.OPERATOR,
        status=status,
        service_category=category,
        description="Test order",
        city="tehran",
        address="Test",
        phone="0912",
    )


def _make_accepted_offer(tenant, order, supplier, *, price_amount=Decimal("9000000")):
    return OrderOffer.objects.create(
        tenant=tenant,
        order=order,
        supplier=supplier,
        price_amount=price_amount,
        currency="IRR",
        status=OrderOfferStatus.ACCEPTED,
        submitted_by=None,
    )


class MarketplaceOfferPriceAuthorityTest(TestCase):
    """Accepted offer price is the authoritative amount for marketplace invoices."""

    def setUp(self):
        self.tenant = _make_tenant()
        self.supplier = _make_supplier(self.tenant)
        self.order = _make_order(self.tenant)
        self.offer = _make_accepted_offer(self.tenant, self.order, self.supplier, price_amount=Decimal("9000000"))

    def test_accepted_offer_price_is_used(self):
        amount = PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)
        self.assertEqual(amount, 9000000)

    def test_pricing_engine_quote_is_ignored_for_marketplace_order(self):
        """Even if a Quote exists with a different amount, the offer price wins."""
        from apps.pricing.models import Quote

        Quote.objects.create(
            tenant=self.tenant,
            order=self.order,
            total_amount=Decimal("12000000"),
            currency="IRR",
        )
        amount = PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)
        self.assertEqual(amount, 9000000)  # Offer price, NOT Quote

    def test_supplier_mismatch_fails_closed(self):
        other_supplier = _make_supplier(self.tenant)
        with self.assertRaises(PreServicePaymentError):
            PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=other_supplier)

    def test_zero_price_rejected(self):
        self.offer.price_amount = Decimal("0")
        self.offer.save(update_fields=["price_amount"])
        with self.assertRaises(PreServicePaymentError):
            PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)

    def test_negative_price_rejected(self):
        self.offer.price_amount = Decimal("-100")
        self.offer.save(update_fields=["price_amount"])
        with self.assertRaises(PreServicePaymentError):
            PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)

    def test_cross_tenant_offer_not_used(self):
        """An accepted offer in another tenant cannot pollute this order's price."""
        other_tenant = _make_tenant()
        other_supplier = _make_supplier(other_tenant)
        # Create an offer in the wrong tenant with the same order reference
        # (shouldn't match due to tenant_id filter)
        OrderOffer.objects.create(
            tenant=other_tenant,
            order=self.order,  # Same order but different tenant on the offer
            supplier=other_supplier,
            price_amount=Decimal("99000000"),
            currency="IRR",
            status=OrderOfferStatus.ACCEPTED,
            submitted_by=None,
        )
        # The original correct-tenant offer should still be used
        amount = PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)
        self.assertEqual(amount, 9000000)

    def test_non_accepted_statuses_not_used(self):
        """Marketplace order with offers but no ACCEPTED one fails closed."""
        # Change our accepted offer to WITHDRAWN
        self.offer.status = OrderOfferStatus.WITHDRAWN
        self.offer.save(update_fields=["status"])
        # A SUBMITTED offer exists — proves this IS a marketplace order
        OrderOffer.objects.create(
            tenant=self.tenant,
            order=self.order,
            supplier=self.supplier,
            price_amount=Decimal("8000000"),
            currency="IRR",
            status=OrderOfferStatus.SUBMITTED,
            submitted_by=None,
        )
        # Marketplace order without ACCEPTED offer → must fail closed, NOT fall back to Quote
        with self.assertRaises(PreServicePaymentError) as ctx:
            PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)
        self.assertIn("no ACCEPTED offer", str(ctx.exception))


class MultipleAcceptedOffersFailClosedTest(TestCase):
    """Multiple accepted offers is an invariant violation — must fail, not silently pick one."""

    def test_multiple_accepted_offers_raises(self):
        tenant = _make_tenant()
        supplier1 = _make_supplier(tenant)
        supplier2 = _make_supplier(tenant)
        order = _make_order(tenant)
        # Normally impossible due to constraints, but test the guard
        OrderOffer.objects.create(
            tenant=tenant,
            order=order,
            supplier=supplier1,
            price_amount=Decimal("5000000"),
            currency="IRR",
            status=OrderOfferStatus.ACCEPTED,
            submitted_by=None,
        )
        OrderOffer.objects.create(
            tenant=tenant,
            order=order,
            supplier=supplier2,
            price_amount=Decimal("6000000"),
            currency="IRR",
            status=OrderOfferStatus.ACCEPTED,
            submitted_by=None,
        )
        with self.assertRaises(PreServicePaymentError):
            PreServicePaymentService._resolve_amount_irr(order=order, supplier=supplier1)


class NonMarketplaceOrderFallbackTest(TestCase):
    """Orders without accepted offers use the existing pricing engine path."""

    def setUp(self):
        self.tenant = _make_tenant()
        self.supplier = _make_supplier(self.tenant)
        self.order = _make_order(self.tenant)

    def test_no_accepted_offer_uses_quote(self):
        """If a Quote exists for the order, it is used."""
        from apps.pricing.models import Quote

        Quote.objects.create(
            tenant=self.tenant,
            order=self.order,
            total_amount=Decimal("7500000"),
            currency="IRR",
        )
        amount = PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)
        self.assertEqual(amount, 7500000)

    def test_no_offer_no_quote_no_rules_fails(self):
        """No accepted offer and no pricing data fails explicitly."""
        with self.assertRaises(PreServicePaymentError):
            PreServicePaymentService._resolve_amount_irr(order=self.order, supplier=self.supplier)


class PriceImmutabilityTest(TestCase):
    """Once a FinancialDocument is created from the offer price, later offer
    edits cannot change it (the service layer prevents editing ACCEPTED offers,
    and the document captures the amount at creation time, not as a live FK)."""

    def test_offer_cannot_be_edited_after_acceptance(self):
        """OrderOfferService.edit_offer() is blocked for non-SUBMITTED offers."""
        tenant = _make_tenant()
        supplier = _make_supplier(tenant)
        order = _make_order(tenant)
        offer = _make_accepted_offer(tenant, order, supplier, price_amount=Decimal("9000000"))
        # The model's can_edit property
        self.assertFalse(offer.can_edit)
        # The is_terminal property
        self.assertTrue(offer.is_terminal)
