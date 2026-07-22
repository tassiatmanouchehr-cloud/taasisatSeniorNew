"""
Tests for OrderOfferService -- Sprint 5.2: Selection and Hold Expiration.

Covers: select_offer(), expire_held_offers() -- authorization, ownership,
state validation, competing-offer rejection, hold mechanics, expiration,
concurrency, audit.
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.kernel.models.audit import AuditLog
from apps.orders.models import OrderOffer, OrderOfferStatus, OrderStatus
from apps.orders.services.order_offer_service import (
    SELECTION_HOLD_DURATION,
    OrderOfferError,
    OrderOfferService,
)

from .helpers import make_order, make_supplier, make_tenant, make_user


def _create_submitted_offer(tenant, order, supplier, actor):
    """Create a SUBMITTED offer directly (bypassing submit_offer's RBAC for test speed)."""
    return OrderOffer.objects.create(
        tenant=tenant,
        order=order,
        supplier=supplier,
        price_amount=Decimal("500000.00"),
        currency="IRR",
        status=OrderOfferStatus.SUBMITTED,
        submitted_by=actor,
    )


class SelectOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)
        self.supplier_actor = make_user(self.tenant)
        self.offer = _create_submitted_offer(self.tenant, self.order, self.supplier, self.supplier_actor)

    def test_successful_selection(self):
        result = OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(result.status, OrderOfferStatus.SELECTED)
        self.assertEqual(result.selected_by_id, self.customer.id)
        self.assertIsNotNone(result.selected_at)
        self.assertIsNotNone(result.hold_expires_at)

    def test_hold_expires_at_is_30_minutes_from_now(self):
        before = timezone.now()
        result = OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        after = timezone.now()
        # hold_expires_at should be within [before+30min, after+30min]
        self.assertGreaterEqual(result.hold_expires_at, before + SELECTION_HOLD_DURATION)
        self.assertLessEqual(result.hold_expires_at, after + SELECTION_HOLD_DURATION)

    def test_selection_records_audit(self):
        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        audit = AuditLog.objects.filter(action="orders.offer.selected").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.resource_id, self.offer.id)

    def test_competing_offers_become_rejected(self):
        supplier2 = make_supplier(self.tenant)
        supplier2_actor = make_user(self.tenant)
        offer2 = _create_submitted_offer(self.tenant, self.order, supplier2, supplier2_actor)

        supplier3 = make_supplier(self.tenant)
        supplier3_actor = make_user(self.tenant)
        offer3 = _create_submitted_offer(self.tenant, self.order, supplier3, supplier3_actor)

        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )

        offer2.refresh_from_db()
        offer3.refresh_from_db()
        self.assertEqual(offer2.status, OrderOfferStatus.REJECTED)
        self.assertEqual(offer3.status, OrderOfferStatus.REJECTED)

    def test_terminal_competing_offers_unchanged(self):
        supplier2 = make_supplier(self.tenant)
        supplier2_actor = make_user(self.tenant)
        offer2 = _create_submitted_offer(self.tenant, self.order, supplier2, supplier2_actor)
        # Manually set to WITHDRAWN (terminal)
        offer2.status = OrderOfferStatus.WITHDRAWN
        offer2.save(update_fields=["status"])

        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )

        offer2.refresh_from_db()
        self.assertEqual(offer2.status, OrderOfferStatus.WITHDRAWN)  # unchanged

    def test_rejection_audit_recorded(self):
        supplier2 = make_supplier(self.tenant)
        supplier2_actor = make_user(self.tenant)
        _create_submitted_offer(self.tenant, self.order, supplier2, supplier2_actor)

        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )

        audit = AuditLog.objects.filter(action="orders.offer.rejected").first()
        self.assertIsNotNone(audit)

    def test_no_assignment_created(self):
        from apps.booking.models import SupplierAssignment

        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(SupplierAssignment.objects.count(), 0)

    def test_order_status_remains_new(self):
        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)


class SelectOfferAuthorizationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.other_user = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)
        self.supplier_actor = make_user(self.tenant)
        self.offer = _create_submitted_offer(self.tenant, self.order, self.supplier, self.supplier_actor)

    def test_non_owner_cannot_select(self):
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.select_offer(
                offer_id=self.offer.id,
                actor=self.other_user,
                tenant_id=self.tenant.id,
            )
        self.assertIn("owner", str(ctx.exception).lower())

    def test_cross_tenant_select_rejected(self):
        other_tenant = make_tenant(prefix="other")
        with self.assertRaises(OrderOfferError):
            OrderOfferService.select_offer(
                offer_id=self.offer.id,
                actor=self.customer,
                tenant_id=other_tenant.id,
            )

    def test_none_actor_rejected(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.select_offer(
                offer_id=self.offer.id,
                actor=None,
                tenant_id=self.tenant.id,
            )


class SelectOfferStateValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)
        self.supplier_actor = make_user(self.tenant)
        self.offer = _create_submitted_offer(self.tenant, self.order, self.supplier, self.supplier_actor)

    def test_non_submitted_offer_rejected(self):
        self.offer.status = OrderOfferStatus.WITHDRAWN
        self.offer.save(update_fields=["status"])

        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.select_offer(
                offer_id=self.offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )
        self.assertIn("cannot be selected", str(ctx.exception).lower())

    def test_order_not_in_new_status_rejected(self):
        self.order.status = OrderStatus.WAITING_SERVICE
        self.order.save(update_fields=["status"])

        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.select_offer(
                offer_id=self.offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )
        self.assertIn("new status", str(ctx.exception).lower())

    def test_already_selected_offer_on_order_rejected(self):
        # Select the first offer
        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        # Create another offer and try to select it
        supplier2 = make_supplier(self.tenant)
        supplier2_actor = make_user(self.tenant)
        offer2 = _create_submitted_offer(self.tenant, self.order, supplier2, supplier2_actor)

        # offer2 should already be REJECTED by the first selection
        offer2.refresh_from_db()
        self.assertEqual(offer2.status, OrderOfferStatus.REJECTED)

        # Even if we manually force it back to SUBMITTED (simulating a race),
        # the DB constraint would block it
        offer2.status = OrderOfferStatus.SUBMITTED
        offer2.save(update_fields=["status"])

        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.select_offer(
                offer_id=offer2.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )
        self.assertIn("already been selected", str(ctx.exception).lower())

    def test_nonexistent_offer_rejected(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.select_offer(
                offer_id=uuid.uuid4(),
                actor=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_offers_for_other_orders_unaffected(self):
        other_order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        other_supplier = make_supplier(self.tenant)
        other_actor = make_user(self.tenant)
        other_offer = _create_submitted_offer(self.tenant, other_order, other_supplier, other_actor)

        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )

        other_offer.refresh_from_db()
        self.assertEqual(other_offer.status, OrderOfferStatus.SUBMITTED)  # unchanged


class ExpireHeldOffersTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)
        self.supplier_actor = make_user(self.tenant)

    def _make_selected_offer(self, *, hold_expires_at):
        offer = _create_submitted_offer(self.tenant, self.order, self.supplier, self.supplier_actor)
        offer.status = OrderOfferStatus.SELECTED
        offer.selected_by = self.customer
        offer.selected_at = timezone.now()
        offer.hold_expires_at = hold_expires_at
        offer.save(update_fields=["status", "selected_by", "selected_at", "hold_expires_at"])
        return offer

    def test_expired_offer_becomes_expired(self):
        past = timezone.now() - timedelta(minutes=1)
        offer = self._make_selected_offer(hold_expires_at=past)

        now = timezone.now()
        result = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=now)

        self.assertEqual(result, [offer.id])
        offer.refresh_from_db()
        self.assertEqual(offer.status, OrderOfferStatus.EXPIRED)

    def test_future_hold_remains_selected(self):
        future = timezone.now() + timedelta(minutes=15)
        offer = self._make_selected_offer(hold_expires_at=future)

        now = timezone.now()
        result = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=now)

        self.assertEqual(result, [])
        offer.refresh_from_db()
        self.assertEqual(offer.status, OrderOfferStatus.SELECTED)

    def test_non_selected_offer_untouched(self):
        offer = _create_submitted_offer(self.tenant, self.order, self.supplier, self.supplier_actor)

        result = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=timezone.now())

        self.assertEqual(result, [])
        offer.refresh_from_db()
        self.assertEqual(offer.status, OrderOfferStatus.SUBMITTED)

    def test_already_terminal_offer_untouched(self):
        offer = _create_submitted_offer(self.tenant, self.order, self.supplier, self.supplier_actor)
        offer.status = OrderOfferStatus.ACCEPTED
        offer.save(update_fields=["status"])

        result = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=timezone.now())
        self.assertEqual(result, [])

    def test_multiple_expired_offers_processed(self):
        past = timezone.now() - timedelta(minutes=5)
        # Need different orders because of one-selected-per-order constraint
        order2 = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        supplier2 = make_supplier(self.tenant)

        offer1 = self._make_selected_offer(hold_expires_at=past)
        offer2 = OrderOffer.objects.create(
            tenant=self.tenant, order=order2, supplier=supplier2,
            price_amount=Decimal("100000"), status=OrderOfferStatus.SELECTED,
            submitted_by=self.supplier_actor, selected_by=self.customer,
            selected_at=timezone.now(), hold_expires_at=past,
        )

        result = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=timezone.now())
        self.assertEqual(set(result), {offer1.id, offer2.id})

    def test_batch_size_honored(self):
        past = timezone.now() - timedelta(minutes=5)
        # Create 3 expired offers on different orders
        for i in range(3):
            order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
            supplier = make_supplier(self.tenant)
            OrderOffer.objects.create(
                tenant=self.tenant, order=order, supplier=supplier,
                price_amount=Decimal("100000"), status=OrderOfferStatus.SELECTED,
                submitted_by=self.supplier_actor, selected_by=self.customer,
                selected_at=timezone.now(), hold_expires_at=past,
            )

        result = OrderOfferService.expire_held_offers(
            tenant_id=self.tenant.id, now=timezone.now(), batch_size=2
        )
        self.assertEqual(len(result), 2)  # Only 2 processed

    def test_idempotent_repeated_execution(self):
        past = timezone.now() - timedelta(minutes=1)
        offer = self._make_selected_offer(hold_expires_at=past)

        now = timezone.now()
        result1 = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=now)
        result2 = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=now)

        self.assertEqual(result1, [offer.id])
        self.assertEqual(result2, [])  # No-op on second call

    def test_expiry_records_audit(self):
        past = timezone.now() - timedelta(minutes=1)
        self._make_selected_offer(hold_expires_at=past)

        OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=timezone.now())

        audit = AuditLog.objects.filter(action="orders.offer.expired").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_type, "system")

    def test_tenant_scoping(self):
        other_tenant = make_tenant(prefix="other")
        other_customer = make_user(other_tenant)
        other_order = make_order(other_tenant, status=OrderStatus.NEW, customer_user=other_customer)
        other_supplier = make_supplier(other_tenant)
        past = timezone.now() - timedelta(minutes=1)
        OrderOffer.objects.create(
            tenant=other_tenant, order=other_order, supplier=other_supplier,
            price_amount=Decimal("100000"), status=OrderOfferStatus.SELECTED,
            submitted_by=make_user(other_tenant), selected_by=other_customer,
            selected_at=timezone.now(), hold_expires_at=past,
        )

        # Only process self.tenant — other tenant's expired offer should be untouched
        result = OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=timezone.now())
        self.assertEqual(result, [])

    def test_global_expiry_processes_all_tenants(self):
        past = timezone.now() - timedelta(minutes=1)
        offer = self._make_selected_offer(hold_expires_at=past)

        result = OrderOfferService.expire_held_offers(tenant_id=None, now=timezone.now())
        self.assertIn(offer.id, result)

    def test_order_status_unchanged_after_expiry(self):
        past = timezone.now() - timedelta(minutes=1)
        self._make_selected_offer(hold_expires_at=past)

        OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=timezone.now())

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)

    def test_no_assignment_created_on_expiry(self):
        from apps.booking.models import SupplierAssignment

        past = timezone.now() - timedelta(minutes=1)
        self._make_selected_offer(hold_expires_at=past)

        OrderOfferService.expire_held_offers(tenant_id=self.tenant.id, now=timezone.now())
        self.assertEqual(SupplierAssignment.objects.count(), 0)
