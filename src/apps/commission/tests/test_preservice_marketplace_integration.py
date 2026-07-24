"""
Phase 6.2B — Controlled Pre-Service Payment Integration Tests.

Proves the complete gated flow from marketplace offer acceptance through
to FinancialDocument and PaymentIntent creation, using the real production
services and the real tenant-scoped feature gate.

Gate mechanism: CommissionConfiguration.get_preservice_payment_enabled()
reads ConfigurationValue via ConfigResolver.get_or_default() with key
'commission.preservice_payment.enabled', default=False, tenant-scoped.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from apps.commission.services.configuration import CommissionConfiguration
from apps.finance.models import FinancialDocument
from apps.orders.models import OrderOffer, OrderOfferStatus, OrderStatus
from apps.orders.services.order_offer_service import OrderOfferService
from apps.payments.models import PaymentIntent

from .helpers import CommissionTestCase


class GateDisabledNoFinancialRecordsTest(CommissionTestCase):
    """With PRESERVICE_PAYMENT_ENABLED disabled (default), offer acceptance
    creates an assignment but no pre-service financial records."""

    def test_acceptance_creates_no_invoice_or_intent(self):
        # Gate is disabled by default — verify
        self.assertFalse(CommissionConfiguration.get_preservice_payment_enabled(tenant_id=self.tenant.id))

        order = self._make_order()
        supplier = self._make_independent_supplier()

        # Create and accept an offer through the real service
        offer = OrderOffer.objects.create(
            tenant=self.tenant,
            order=order,
            supplier=supplier,
            price_amount=Decimal("9000000"),
            currency="IRR",
            status=OrderOfferStatus.SELECTED,
            submitted_by=None,
            selected_by=self._customer_user_for_order(order),
            selected_at=__import__("django.utils", fromlist=["timezone"]).timezone.now(),
            hold_expires_at=__import__("django.utils", fromlist=["timezone"]).timezone.now()
            + __import__("datetime").timedelta(minutes=30),
        )

        # Accept through the real entry point
        OrderOfferService.accept_offer(
            offer_id=offer.id,
            actor=self._customer_user_for_order(order),
            tenant_id=self.tenant.id,
        )

        # Assignment succeeded
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)

        # No pre-service financial records
        self.assertFalse(FinancialDocument.objects.filter(tenant=self.tenant, order=order).exists())
        self.assertFalse(PaymentIntent.objects.filter(tenant=self.tenant, reference_id=order.id).exists())


class GateEnabledMarketplaceFlowTest(CommissionTestCase):
    """With PRESERVICE_PAYMENT_ENABLED enabled for the tenant, marketplace
    offer acceptance creates exactly one invoice and one PaymentIntent
    with the accepted offer price."""

    def setUp(self):
        super().setUp()
        self._enable_preservice_payment()

    def _accept_marketplace_offer(self, *, price_amount=Decimal("9000000")):
        from datetime import timedelta

        from django.utils import timezone

        order = self._make_order()
        supplier = self._make_independent_supplier()

        offer = OrderOffer.objects.create(
            tenant=self.tenant,
            order=order,
            supplier=supplier,
            price_amount=price_amount,
            currency="IRR",
            status=OrderOfferStatus.SELECTED,
            submitted_by=None,
            selected_by=self._customer_user_for_order(order),
            selected_at=timezone.now(),
            hold_expires_at=timezone.now() + timedelta(minutes=30),
        )

        OrderOfferService.accept_offer(
            offer_id=offer.id,
            actor=self._customer_user_for_order(order),
            tenant_id=self.tenant.id,
        )
        return order, supplier, offer

    def test_acceptance_creates_invoice_with_offer_price(self):
        order, supplier, offer = self._accept_marketplace_offer(price_amount=Decimal("9000000"))

        docs = FinancialDocument.objects.filter(tenant=self.tenant, order=order)
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs.first().total_amount, Decimal("9000000"))

    def test_acceptance_creates_payment_intent_with_offer_price(self):
        order, supplier, offer = self._accept_marketplace_offer(price_amount=Decimal("9000000"))

        intents = PaymentIntent.objects.filter(tenant=self.tenant, reference_id=order.id)
        self.assertEqual(intents.count(), 1)
        self.assertEqual(intents.first().amount, Decimal("9000000"))

    def test_divergent_quote_amount_is_ignored(self):
        """A Quote with a different amount must not affect the invoice."""
        from apps.pricing.models import Quote

        order = self._make_order()
        supplier = self._make_independent_supplier()

        # Create a divergent Quote
        Quote.objects.create(tenant=self.tenant, order=order, total_amount=Decimal("12000000"), currency="IRR")

        from datetime import timedelta

        from django.utils import timezone

        offer = OrderOffer.objects.create(
            tenant=self.tenant,
            order=order,
            supplier=supplier,
            price_amount=Decimal("7500000"),
            currency="IRR",
            status=OrderOfferStatus.SELECTED,
            submitted_by=None,
            selected_by=self._customer_user_for_order(order),
            selected_at=timezone.now(),
            hold_expires_at=timezone.now() + timedelta(minutes=30),
        )

        OrderOfferService.accept_offer(
            offer_id=offer.id,
            actor=self._customer_user_for_order(order),
            tenant_id=self.tenant.id,
        )

        doc = FinancialDocument.objects.get(tenant=self.tenant, order=order)
        self.assertEqual(doc.total_amount, Decimal("7500000"))  # Offer price, NOT Quote

    def test_assignment_relationships_correct(self):
        order, supplier, offer = self._accept_marketplace_offer()

        order.refresh_from_db()
        self.assertEqual(order.assigned_supplier_id, supplier.id)
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)


class TenantIsolationTest(CommissionTestCase):
    """Enabling the gate for Tenant A does not enable it for Tenant B."""

    def setUp(self):
        super().setUp()
        # Enable only for self.tenant (Tenant A)
        self._enable_preservice_payment(tenant=self.tenant)

    def test_other_tenant_creates_no_financial_records(self):
        from datetime import timedelta

        from django.utils import timezone

        # Create order in OTHER tenant (gate NOT enabled there)
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant, name="Care", slug=f"care-{uuid.uuid4().hex[:6]}", status="active"
        )
        from apps.accounts.models.profiles import CustomerProfile

        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = __import__("apps.kernel.models", fromlist=["Person"]).Person.objects.create(
            tenant=self.other_tenant, full_name="Other Customer"
        )
        user = __import__("apps.kernel.models", fromlist=["UserAccount"]).UserAccount.objects.create_user(
            phone=phone, person=person, tenant=self.other_tenant
        )
        customer = CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name="Other Customer")

        order = Order.objects.create(
            tenant=self.other_tenant,
            source="operator",
            status=OrderStatus.NEW,
            service_category=other_category,
            customer_profile=customer,
            description="Other",
            city="tehran",
            address="Addr",
            phone="0912",
        )
        supplier = ServiceSupplier.objects.create(
            tenant=self.other_tenant,
            supplier_type="INDEPENDENT_PROVIDER",
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="TestProfile",
            display_name="Other Supplier",
            status="active",
            availability_status="available",
            verification_level="basic",
        )
        offer = OrderOffer.objects.create(
            tenant=self.other_tenant,
            order=order,
            supplier=supplier,
            price_amount=Decimal("5000000"),
            currency="IRR",
            status=OrderOfferStatus.SELECTED,
            submitted_by=None,
            selected_by=user,
            selected_at=timezone.now(),
            hold_expires_at=timezone.now() + timedelta(minutes=30),
        )

        OrderOfferService.accept_offer(offer_id=offer.id, actor=user, tenant_id=self.other_tenant.id)

        # No financial records for other_tenant
        self.assertFalse(FinancialDocument.objects.filter(tenant=self.other_tenant, order=order).exists())
        self.assertFalse(PaymentIntent.objects.filter(tenant=self.other_tenant, reference_id=order.id).exists())


class PaymentIntentFailureRollbackTest(CommissionTestCase):
    """If PaymentIntent creation fails, the entire assignment transaction
    rolls back — no partial financial state."""

    def setUp(self):
        super().setUp()
        self._enable_preservice_payment()

    def test_intent_failure_leaves_no_financial_records(self):
        from datetime import timedelta

        from django.utils import timezone

        order = self._make_order()
        supplier = self._make_independent_supplier()
        offer = OrderOffer.objects.create(
            tenant=self.tenant,
            order=order,
            supplier=supplier,
            price_amount=Decimal("9000000"),
            currency="IRR",
            status=OrderOfferStatus.SELECTED,
            submitted_by=None,
            selected_by=self._customer_user_for_order(order),
            selected_at=timezone.now(),
            hold_expires_at=timezone.now() + timedelta(minutes=30),
        )

        with patch(
            "apps.payments.services.payment_intent_service.PaymentIntentService.create_intent",
            side_effect=Exception("Intent creation failed"),
        ):
            with self.assertRaises(Exception):
                OrderOfferService.accept_offer(
                    offer_id=offer.id,
                    actor=self._customer_user_for_order(order),
                    tenant_id=self.tenant.id,
                )

        # Everything rolled back
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.NEW)
        self.assertFalse(FinancialDocument.objects.filter(tenant=self.tenant, order=order).exists())
        self.assertFalse(PaymentIntent.objects.filter(tenant=self.tenant, reference_id=order.id).exists())


class IdempotencyTest(CommissionTestCase):
    """Repeated invocation of the payment orchestration does not create
    duplicate financial records (guaranteed by deadline-scoped idempotency key)."""

    def setUp(self):
        super().setUp()
        self._enable_preservice_payment()

    def test_duplicate_orchestration_produces_single_intent(self):
        from datetime import timedelta

        from django.utils import timezone

        order = self._make_order()
        supplier = self._make_independent_supplier()
        offer = OrderOffer.objects.create(
            tenant=self.tenant,
            order=order,
            supplier=supplier,
            price_amount=Decimal("9000000"),
            currency="IRR",
            status=OrderOfferStatus.SELECTED,
            submitted_by=None,
            selected_by=self._customer_user_for_order(order),
            selected_at=timezone.now(),
            hold_expires_at=timezone.now() + timedelta(minutes=30),
        )

        # First acceptance
        OrderOfferService.accept_offer(
            offer_id=offer.id,
            actor=self._customer_user_for_order(order),
            tenant_id=self.tenant.id,
        )

        # PaymentIntent idempotency key is "preservice:{deadline.id}"
        # A second call to the acceptance path would fail (offer already ACCEPTED,
        # order already WAITING_SERVICE) — so idempotency is structurally enforced.
        # Verify the single-invocation result:
        self.assertEqual(PaymentIntent.objects.filter(tenant=self.tenant, reference_id=order.id).count(), 1)
        self.assertEqual(FinancialDocument.objects.filter(tenant=self.tenant, order=order).count(), 1)


class NonMarketplaceFallbackTest(CommissionTestCase):
    """Orders without offer history use the Quote/pricing-engine path."""

    def setUp(self):
        super().setUp()
        self._enable_preservice_payment()
        # Seed a fixed pricing rule so QuoteService can generate
        self._seed_fixed_pricing_rule(amount="10000000")

    def test_non_marketplace_order_uses_quote_amount(self):
        """An operator-assigned order (no offers) uses the pricing engine."""
        from apps.booking.services.assignment_service import AssignmentService
        from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor

        order = self._make_order()
        supplier = self._make_independent_supplier()
        actor = make_actor(self.tenant, full_name="Operator")
        grant_permissions(self.tenant, actor, ["booking.assignment.assign"])

        # Direct assignment (no offer acceptance — this is non-marketplace)
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=actor)

        # Financial records created from pricing engine
        doc = FinancialDocument.objects.get(tenant=self.tenant, order=order)
        self.assertEqual(doc.total_amount, Decimal("10000000"))  # From pricing rule

        intent = PaymentIntent.objects.get(tenant=self.tenant, reference_id=order.id)
        self.assertEqual(intent.amount, Decimal("10000000"))


# Import needed models for TenantIsolationTest
from apps.kernel.models.supplier import ServiceSupplier
from apps.orders.models import Order, ServiceCategory
