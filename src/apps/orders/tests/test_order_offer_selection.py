"""
Tests for OrderOfferService -- Sprint 5.2: Selection and Hold Expiration.

Covers: select_offer(), expire_held_offers() -- authorization, ownership,
state validation, competing-offer rejection, hold mechanics, expiration,
concurrency, audit.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

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
        # Create the second offer BEFORE the first selection, so it is present
        # when select_offer() bulk-rejects competing SUBMITTED offers.
        supplier2 = make_supplier(self.tenant)
        supplier2_actor = make_user(self.tenant)
        offer2 = _create_submitted_offer(self.tenant, self.order, supplier2, supplier2_actor)

        # Select the first offer
        OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )

        # offer2 should now be REJECTED by the first selection's bulk-reject step
        offer2.refresh_from_db()
        self.assertEqual(offer2.status, OrderOfferStatus.REJECTED)

        # Attempting to select the now-REJECTED offer must raise a domain error,
        # not a raw IntegrityError.
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.select_offer(
                offer_id=offer2.id,
                actor=self.customer,
                tenant_id=self.tenant.id,
            )
        self.assertIn("cannot be selected", str(ctx.exception).lower())

        # Exactly one offer remains SELECTED.
        selected_count = OrderOffer.objects.filter(
            order=self.order, status=OrderOfferStatus.SELECTED
        ).count()
        self.assertEqual(selected_count, 1)

        # Parent order status remains unchanged.
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)

        # No assignment or downstream artifact was created.
        from apps.booking.models import SupplierAssignment

        self.assertEqual(SupplierAssignment.objects.count(), 0)

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
        for _i in range(3):
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



# --- Remediation: Real Concurrency Test (PR #44 review finding F3) ----------


import threading

from django.apps import apps as django_apps
from django.db import connection
from django.test import TransactionTestCase as RealTransactionTestCase

from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, ServiceCategory


class ConcurrentSelectionTest(RealTransactionTestCase):
    """Prove that two concurrent select_offer() calls for the same order
    produce exactly one SELECTED offer, with the loser receiving a domain
    error (not a raw IntegrityError).

    Uses TransactionTestCase with real threading and separate DB connections,
    matching apps/booking/tests/test_concurrency.py and
    apps/availability/tests/test_concurrency.py patterns exactly.
    """

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug=f"sel-race-{uuid.uuid4().hex[:8]}",
            name="Selection Race Tenant",
        )
        person = Person.objects.create(tenant=self.tenant, full_name="Customer")
        self.customer = UserAccount.objects.create_user(
            phone="09121111111", person=person, tenant=self.tenant,
        )
        category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Care", slug="care-race",
            status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=category, description="Race order",
            city="tehran", address="Addr", phone="09120000000",
            created_by=self.customer,
        )
        # Two SUBMITTED offers from different suppliers
        self.supplier_a = ServiceSupplier.objects.create(
            tenant=self.tenant, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile",
            display_name="A", status=SupplierStatus.ACTIVE,
            availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.supplier_b = ServiceSupplier.objects.create(
            tenant=self.tenant, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(), linked_entity_type="TestProfile",
            display_name="B", status=SupplierStatus.ACTIVE,
            availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        submitter = UserAccount.objects.create_user(
            phone="09122222222",
            person=Person.objects.create(tenant=self.tenant, full_name="Submitter"),
            tenant=self.tenant,
        )
        self.offer_a = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000"), status=OrderOfferStatus.SUBMITTED,
            submitted_by=submitter,
        )
        self.offer_b = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_b,
            price_amount=Decimal("600000"), status=OrderOfferStatus.SUBMITTED,
            submitted_by=submitter,
        )

    def _run_concurrently(self, callables):
        """Run each callable in its own thread, synchronized via Barrier."""
        barrier = threading.Barrier(len(callables))
        results = [None] * len(callables)

        def _wrap(index, fn):
            try:
                barrier.wait(timeout=5)
                value = fn()
                results[index] = ("ok", value)
            except Exception as exc:
                results[index] = ("error", exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=_wrap, args=(i, fn)) for i, fn in enumerate(callables)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
        return results

    def test_concurrent_selection_produces_exactly_one_winner(self):
        """Two threads each try to select a different offer for the same order.
        Exactly one must succeed; the other must receive OrderOfferError."""

        def select_a():
            return OrderOfferService.select_offer(
                offer_id=self.offer_a.id, actor=self.customer, tenant_id=self.tenant.id,
            )

        def select_b():
            return OrderOfferService.select_offer(
                offer_id=self.offer_b.id, actor=self.customer, tenant_id=self.tenant.id,
            )

        results = self._run_concurrently([select_a, select_b])

        # Exactly one OK, one error
        ok_count = sum(1 for r in results if r[0] == "ok")
        error_count = sum(1 for r in results if r[0] == "error")
        self.assertEqual(ok_count, 1, f"Expected exactly 1 success, got {ok_count}: {results}")
        self.assertEqual(error_count, 1, f"Expected exactly 1 error, got {error_count}: {results}")

        # The error must be OrderOfferError (not raw IntegrityError)
        error_result = next(r for r in results if r[0] == "error")
        self.assertIsInstance(error_result[1], OrderOfferError)

        # Database state: exactly one SELECTED offer
        selected_count = OrderOffer.objects.filter(
            order=self.order, status=OrderOfferStatus.SELECTED
        ).count()
        self.assertEqual(selected_count, 1)

        # The losing offer is either REJECTED (if the winner's bulk-reject ran)
        # or still SUBMITTED (if the loser's transaction rolled back before
        # the winner's competing-offer rejection committed). Both are acceptable
        # final states — the invariant is: at most one SELECTED.
        non_selected = OrderOffer.objects.filter(order=self.order).exclude(
            status=OrderOfferStatus.SELECTED
        )
        for offer in non_selected:
            self.assertIn(
                offer.status,
                [OrderOfferStatus.SUBMITTED, OrderOfferStatus.REJECTED],
            )

        # Parent order unchanged
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)

        # No assignment/booking created
        from apps.booking.models import SupplierAssignment
        self.assertEqual(SupplierAssignment.objects.count(), 0)

        # Audit: exactly one "selected" entry
        from apps.kernel.models.audit import AuditLog
        selected_audits = AuditLog.objects.filter(action="orders.offer.selected").count()
        self.assertEqual(selected_audits, 1)


# --- Remediation: CustomerProfile ownership-path test (PR #44 review finding F2) ---


from apps.accounts.models.profiles import CustomerProfile


class SelectOfferCustomerProfileOwnershipTest(TestCase):
    """Prove that order ownership works through the customer_profile.person path,
    not just the created_by fallback."""

    def setUp(self):
        self.tenant = make_tenant()
        # Create customer with a real CustomerProfile
        self.customer = make_user(self.tenant)
        self.customer_profile = CustomerProfile.objects.create(
            user=self.customer,
            person=self.customer.person,
            phone=self.customer.phone,
        )
        # Create a DIFFERENT user as created_by (operator who placed the order)
        self.operator = make_user(self.tenant)
        # Order has customer_profile set, but created_by is the OPERATOR
        self.order = make_order(self.tenant, status=OrderStatus.NEW, customer_user=self.operator)
        self.order.customer_profile = self.customer_profile
        self.order.save(update_fields=["customer_profile"])

        self.supplier = make_supplier(self.tenant)
        self.supplier_actor = make_user(self.tenant)
        self.offer = _create_submitted_offer(self.tenant, self.order, self.supplier, self.supplier_actor)

    def test_customer_profile_owner_can_select(self):
        """The customer associated via customer_profile.person can select,
        even though created_by is a different user."""
        result = OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(result.status, OrderOfferStatus.SELECTED)
        self.assertEqual(result.selected_by_id, self.customer.id)

    def test_operator_created_by_can_also_select(self):
        """The created_by user (operator) can also select — both paths work."""
        result = OrderOfferService.select_offer(
            offer_id=self.offer.id,
            actor=self.operator,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(result.status, OrderOfferStatus.SELECTED)

    def test_unrelated_user_cannot_select_via_customer_profile(self):
        """A user who is neither customer_profile owner nor created_by is rejected."""
        unrelated = make_user(self.tenant)
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.select_offer(
                offer_id=self.offer.id,
                actor=unrelated,
                tenant_id=self.tenant.id,
            )
        self.assertIn("owner", str(ctx.exception).lower())
