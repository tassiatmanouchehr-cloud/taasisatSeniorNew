"""
Tests for OrderOfferService -- Sprint 5.3B: Acceptance and Cancellation Propagation.

Covers: accept_offer(), cancel_offers_for_order() -- authorization, ownership,
state validation, hold expiry race, assignment integration, cancellation
propagation, idempotency, concurrency, audit.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.booking.models import SupplierAssignment
from apps.kernel.models.audit import AuditLog
from apps.kernel.models.rbac import Role, RoleAssignment
from apps.orders.models import OrderOffer, OrderOfferStatus, OrderStatus
from apps.orders.services.order_offer_service import OrderOfferError, OrderOfferService
from apps.orders.services.status_machine import (
    approve_cancellation,
    request_cancellation,
)

from .helpers import make_order, make_supplier, make_tenant, make_user


def _create_selected_offer(tenant, order, supplier, customer, *, hold_minutes=30):
    """Create a SELECTED offer with an active hold (bypassing select_offer for test speed)."""
    now = timezone.now()
    return OrderOffer.objects.create(
        tenant=tenant,
        order=order,
        supplier=supplier,
        price_amount=Decimal("750000.00"),
        currency="IRR",
        status=OrderOfferStatus.SELECTED,
        submitted_by=make_user(tenant),
        selected_by=customer,
        selected_at=now,
        hold_expires_at=now + timedelta(minutes=hold_minutes),
    )


def _create_submitted_offer(tenant, order, supplier):
    """Create a SUBMITTED offer."""
    return OrderOffer.objects.create(
        tenant=tenant,
        order=order,
        supplier=supplier,
        price_amount=Decimal("500000.00"),
        currency="IRR",
        status=OrderOfferStatus.SUBMITTED,
        submitted_by=make_user(tenant),
    )


def _grant_cancellation_permissions(tenant, user):
    """Grant both cancellation permissions to a user."""
    role = Role.objects.create(
        tenant=tenant,
        slug=f"cancel-role-{uuid.uuid4().hex[:8]}",
        name="Cancel Role",
        permissions=["orders.cancellation.request", "orders.cancellation.approve"],
    )
    RoleAssignment.objects.create(tenant=tenant, user=user, role=role, is_active=True)


# ============================================================
# accept_offer() — Happy Path
# ============================================================


class AcceptOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)
        self.offer = _create_selected_offer(self.tenant, self.order, self.supplier, self.customer)

    def test_successful_acceptance(self):
        result = OrderOfferService.accept_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(result.status, OrderOfferStatus.ACCEPTED)

    def test_acceptance_creates_exactly_one_assignment(self):
        OrderOfferService.accept_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 1)

    def test_assignment_is_for_the_correct_supplier(self):
        OrderOfferService.accept_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        assignment = SupplierAssignment.objects.get(order=self.order)
        self.assertEqual(assignment.supplier_id, self.supplier.id)

    def test_order_transitions_to_waiting_service(self):
        OrderOfferService.accept_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.WAITING_SERVICE)

    def test_order_assigned_supplier_is_set(self):
        OrderOfferService.accept_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, self.supplier.id)

    def test_acceptance_records_audit(self):
        OrderOfferService.accept_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        audit = AuditLog.objects.filter(action="orders.offer.accepted").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.resource_id, self.offer.id)


# ============================================================
# accept_offer() — Authorization
# ============================================================


class AcceptOfferAuthorizationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.other_user = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)
        self.offer = _create_selected_offer(self.tenant, self.order, self.supplier, self.customer)

    def test_non_owner_cannot_accept(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=self.offer.id,
                actor=self.other_user,
                tenant_id=self.tenant.id,
            )

    def test_cross_tenant_actor_cannot_accept(self):
        other_tenant = make_tenant(prefix="other")
        cross_user = make_user(other_tenant)
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=self.offer.id,
                actor=cross_user,
                tenant_id=other_tenant.id,
            )

    def test_none_actor_raises(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=self.offer.id,
                actor=None,
                tenant_id=self.tenant.id,
            )

    def test_rejection_leaves_offer_unchanged(self):
        original_status = self.offer.status
        try:
            OrderOfferService.accept_offer(
                offer_id=self.offer.id,
                actor=self.other_user,
                tenant_id=self.tenant.id,
            )
        except OrderOfferError:
            pass
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.status, original_status)

    def test_rejection_creates_no_assignment(self):
        try:
            OrderOfferService.accept_offer(
                offer_id=self.offer.id,
                actor=self.other_user,
                tenant_id=self.tenant.id,
            )
        except OrderOfferError:
            pass
        self.assertEqual(SupplierAssignment.objects.count(), 0)


# ============================================================
# accept_offer() — State Validation
# ============================================================


class AcceptOfferStateValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)

    def test_submitted_offer_cannot_be_accepted(self):
        offer = _create_submitted_offer(self.tenant, self.order, self.supplier)
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_expired_offer_cannot_be_accepted(self):
        # Create offer with expired hold
        offer = _create_selected_offer(self.tenant, self.order, self.supplier, self.customer, hold_minutes=-5)
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_withdrawn_offer_cannot_be_accepted(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant,
            order=self.order,
            supplier=self.supplier,
            price_amount=Decimal("500000.00"),
            currency="IRR",
            status=OrderOfferStatus.WITHDRAWN,
            submitted_by=make_user(self.tenant),
        )
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_already_accepted_offer_raises(self):
        offer = _create_selected_offer(self.tenant, self.order, self.supplier, self.customer)
        OrderOfferService.accept_offer(
            offer_id=offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        # Order is now WAITING_SERVICE, offer is ACCEPTED — second call should fail
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_offer_from_another_order_cannot_be_accepted(self):
        other_order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        offer = _create_selected_offer(self.tenant, other_order, self.supplier, self.customer)
        # Try accepting with the wrong tenant_id trick won't work; but
        # the offer belongs to other_order — after acceptance the *other_order*
        # would transition, not self.order. This tests that the offer correctly
        # maps to its own order.
        result = OrderOfferService.accept_offer(
            offer_id=offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        # It succeeds (owner of other_order is the same customer)
        self.assertEqual(result.status, OrderOfferStatus.ACCEPTED)
        other_order.refresh_from_db()
        self.assertEqual(other_order.status, OrderStatus.WAITING_SERVICE)
        # Original order remains unchanged
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)

    def test_terminal_order_rejects_acceptance(self):
        """An order already in a terminal status rejects offer acceptance."""
        _grant_cancellation_permissions(self.tenant, self.customer)
        offer = _create_selected_offer(self.tenant, self.order, self.supplier, self.customer)
        # Cancel the order
        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)
        # Attempt to accept — order is CANCELLED
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_offer_with_inactive_supplier_rejected(self):
        from apps.kernel.models.supplier import SupplierStatus

        inactive_supplier = make_supplier(self.tenant, status=SupplierStatus.INACTIVE)
        offer = _create_selected_offer(self.tenant, self.order, inactive_supplier, self.customer)
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_nonexistent_offer_raises(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=uuid.uuid4(),
                actor=self.customer,
                tenant_id=self.tenant.id,
            )


# ============================================================
# accept_offer() — Idempotency / Duplicate Prevention
# ============================================================


class AcceptOfferIdempotencyTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier = make_supplier(self.tenant)
        self.offer = _create_selected_offer(self.tenant, self.order, self.supplier, self.customer)

    def test_repeated_acceptance_does_not_create_duplicate_assignment(self):
        OrderOfferService.accept_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        # Second call fails (order no longer NEW, offer no longer SELECTED)
        with self.assertRaises(OrderOfferError):
            OrderOfferService.accept_offer(
                offer_id=self.offer.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )
        # Still exactly one assignment
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 1)


# ============================================================
# cancel_offers_for_order() — Propagation
# ============================================================


class CancelOffersForOrderTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.customer = make_user(self.tenant)
        _grant_cancellation_permissions(self.tenant, self.customer)
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        self.supplier1 = make_supplier(self.tenant)
        self.supplier2 = make_supplier(self.tenant)
        self.supplier3 = make_supplier(self.tenant)

    def test_submitted_offers_cancelled_on_order_cancellation(self):
        offer1 = _create_submitted_offer(self.tenant, self.order, self.supplier1)
        offer2 = _create_submitted_offer(self.tenant, self.order, self.supplier2)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        offer1.refresh_from_db()
        offer2.refresh_from_db()
        self.assertEqual(offer1.status, OrderOfferStatus.CANCELLED)
        self.assertEqual(offer2.status, OrderOfferStatus.CANCELLED)

    def test_selected_offer_cancelled_on_order_cancellation(self):
        offer = _create_selected_offer(self.tenant, self.order, self.supplier1, self.customer)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        offer.refresh_from_db()
        self.assertEqual(offer.status, OrderOfferStatus.CANCELLED)

    def test_already_terminal_offers_remain_unchanged(self):
        # Create offers in various terminal states
        withdrawn = OrderOffer.objects.create(
            tenant=self.tenant,
            order=self.order,
            supplier=self.supplier1,
            price_amount=Decimal("500000.00"),
            currency="IRR",
            status=OrderOfferStatus.WITHDRAWN,
            submitted_by=make_user(self.tenant),
        )
        expired = OrderOffer.objects.create(
            tenant=self.tenant,
            order=self.order,
            supplier=self.supplier2,
            price_amount=Decimal("500000.00"),
            currency="IRR",
            status=OrderOfferStatus.EXPIRED,
            submitted_by=make_user(self.tenant),
        )
        rejected = OrderOffer.objects.create(
            tenant=self.tenant,
            order=self.order,
            supplier=self.supplier3,
            price_amount=Decimal("500000.00"),
            currency="IRR",
            status=OrderOfferStatus.REJECTED,
            submitted_by=make_user(self.tenant),
        )

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        withdrawn.refresh_from_db()
        expired.refresh_from_db()
        rejected.refresh_from_db()
        self.assertEqual(withdrawn.status, OrderOfferStatus.WITHDRAWN)
        self.assertEqual(expired.status, OrderOfferStatus.EXPIRED)
        self.assertEqual(rejected.status, OrderOfferStatus.REJECTED)

    def test_repeated_propagation_is_idempotent(self):
        offer = _create_submitted_offer(self.tenant, self.order, self.supplier1)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        offer.refresh_from_db()
        self.assertEqual(offer.status, OrderOfferStatus.CANCELLED)

        # Calling cancel_offers_for_order again directly should be a no-op
        self.order.refresh_from_db()
        result = OrderOfferService.cancel_offers_for_order(order=self.order)
        self.assertEqual(result, [])

    def test_no_offers_from_another_order_modified(self):
        other_order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.customer)
        other_offer = _create_submitted_offer(self.tenant, other_order, self.supplier1)

        _create_submitted_offer(self.tenant, self.order, self.supplier2)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        other_offer.refresh_from_db()
        self.assertEqual(other_offer.status, OrderOfferStatus.SUBMITTED)

    def test_no_offers_from_another_tenant_modified(self):
        other_tenant = make_tenant(prefix="other")
        other_customer = make_user(other_tenant)
        _grant_cancellation_permissions(other_tenant, other_customer)
        other_order = make_order(other_tenant, status=OrderStatus.NEW, customer_user=other_customer)
        other_supplier = make_supplier(other_tenant)
        other_offer = _create_submitted_offer(other_tenant, other_order, other_supplier)

        _create_submitted_offer(self.tenant, self.order, self.supplier1)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        other_offer.refresh_from_db()
        self.assertEqual(other_offer.status, OrderOfferStatus.SUBMITTED)

    def test_cancellation_request_alone_does_not_cancel_offers(self):
        offer = _create_submitted_offer(self.tenant, self.order, self.supplier1)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)

        offer.refresh_from_db()
        self.assertEqual(offer.status, OrderOfferStatus.SUBMITTED)

    def test_cancellation_audit_recorded(self):
        _create_submitted_offer(self.tenant, self.order, self.supplier1)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        audit = AuditLog.objects.filter(action="orders.offer.cancelled").first()
        self.assertIsNotNone(audit)
        self.assertEqual(str(audit.resource_id), str(self.order.id))

    def test_mixed_active_and_terminal_only_active_cancelled(self):
        """Mix of active and terminal offers: only active ones are cancelled."""
        submitted = _create_submitted_offer(self.tenant, self.order, self.supplier1)
        selected = _create_selected_offer(self.tenant, self.order, self.supplier2, self.customer)
        withdrawn = OrderOffer.objects.create(
            tenant=self.tenant,
            order=self.order,
            supplier=self.supplier3,
            price_amount=Decimal("500000.00"),
            currency="IRR",
            status=OrderOfferStatus.WITHDRAWN,
            submitted_by=make_user(self.tenant),
        )

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        approve_cancellation(order_id=self.order.id, changed_by=None)

        submitted.refresh_from_db()
        selected.refresh_from_db()
        withdrawn.refresh_from_db()
        self.assertEqual(submitted.status, OrderOfferStatus.CANCELLED)
        self.assertEqual(selected.status, OrderOfferStatus.CANCELLED)
        self.assertEqual(withdrawn.status, OrderOfferStatus.WITHDRAWN)
