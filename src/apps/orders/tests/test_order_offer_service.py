"""
Tests for OrderOfferService — Sprint 5.1: Submission Lifecycle Foundation.

Covers: submit_offer(), edit_offer(), withdraw_offer() — authorization,
tenant isolation, state validation, concurrency, audit, domain errors.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.kernel.models.audit import AuditLog
from apps.kernel.models.supplier import SupplierStatus
from apps.orders.models import OrderOfferStatus, OrderStatus
from apps.orders.services.order_offer_service import OrderOfferError, OrderOfferService

from .helpers import make_order, make_supplier, make_tenant, make_user


class SubmitOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)

    def test_successful_submission(self):
        offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )

        self.assertEqual(offer.status, OrderOfferStatus.SUBMITTED)
        self.assertEqual(offer.order_id, self.order.id)
        self.assertEqual(offer.supplier_id, self.supplier.id)
        self.assertEqual(offer.tenant_id, self.tenant.id)
        self.assertEqual(offer.price_amount, Decimal("500000.00"))
        self.assertEqual(offer.currency, "IRR")
        self.assertEqual(offer.submitted_by_id, self.actor.id)

    def test_submission_records_audit(self):
        offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )

        audit = AuditLog.objects.get(
            tenant_id=self.tenant.id,
            action="orders.offer.submitted",
        )
        self.assertEqual(audit.resource_id, offer.id)
        self.assertEqual(audit.after_snapshot["order_id"], str(self.order.id))

    def test_submission_with_optional_fields(self):
        offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("750000.00"),
            currency="USD",
            estimated_duration_minutes=120,
            terms="Net 30",
            message="Looking forward to working with you",
        )

        self.assertEqual(offer.currency, "USD")
        self.assertEqual(offer.estimated_duration_minutes, 120)
        self.assertEqual(offer.terms, "Net 30")
        self.assertEqual(offer.message, "Looking forward to working with you")


class SubmitOfferValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)

    def test_null_actor_rejected(self):
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=None,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("authenticated actor", str(ctx.exception))

    def test_order_not_in_new_status_rejected(self):
        order = make_order(self.tenant, status=OrderStatus.WAITING_SERVICE)
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("NEW status", str(ctx.exception))

    def test_completed_order_rejected(self):
        order = make_order(self.tenant, status=OrderStatus.COMPLETED)
        with self.assertRaises(OrderOfferError):
            OrderOfferService.submit_offer(
                order_id=order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )

    def test_cancelled_order_rejected(self):
        order = make_order(self.tenant, status=OrderStatus.CANCELLED)
        with self.assertRaises(OrderOfferError):
            OrderOfferService.submit_offer(
                order_id=order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )

    def test_inactive_supplier_rejected(self):
        self.supplier.status = SupplierStatus.INACTIVE
        self.supplier.save()
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("ACTIVE", str(ctx.exception))

    def test_zero_price_rejected(self):
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("0.00"),
            )
        self.assertIn("positive", str(ctx.exception))

    def test_negative_price_rejected(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("-100.00"),
            )

    def test_duplicate_submission_raises_domain_error(self):
        OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("600000.00"),
            )
        self.assertIn("already has an offer", str(ctx.exception))


class SubmitOfferTenantIsolationTest(TestCase):
    def setUp(self):
        self.tenant_a = make_tenant("a")
        self.tenant_b = make_tenant("b")
        self.actor = make_user(self.tenant_a)
        self.supplier = make_supplier(self.tenant_a)
        self.order = make_order(self.tenant_a, status=OrderStatus.NEW)

    def test_cross_tenant_order_not_found(self):
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant_b.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("not found", str(ctx.exception))

    def test_cross_tenant_supplier_not_found(self):
        supplier_b = make_supplier(self.tenant_b)
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=supplier_b.id,
                actor=self.actor,
                tenant_id=self.tenant_a.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("not found", str(ctx.exception))


class SubmitOfferPermissionTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)

    def test_permission_service_is_called(self):
        with patch("apps.orders.services.order_offer_service.PermissionService.require") as mock_require:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )

        mock_require.assert_called_once()
        call_kwargs = mock_require.call_args
        self.assertEqual(call_kwargs[0][1], "orders.offer.submit")


class EditOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        self.offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )

    def test_successful_price_edit(self):
        updated = OrderOfferService.edit_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("600000.00"),
        )

        self.assertEqual(updated.price_amount, Decimal("600000.00"))
        self.assertEqual(updated.status, OrderOfferStatus.SUBMITTED)

    def test_edit_records_audit(self):
        OrderOfferService.edit_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("600000.00"),
        )

        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action="orders.offer.edited",
                resource_id=self.offer.id,
            ).exists()
        )

    def test_edit_multiple_fields(self):
        updated = OrderOfferService.edit_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("700000.00"),
            terms="Updated terms",
            message="Updated message",
        )

        self.assertEqual(updated.price_amount, Decimal("700000.00"))
        self.assertEqual(updated.terms, "Updated terms")
        self.assertEqual(updated.message, "Updated message")

    def test_no_change_is_noop(self):
        """If no fields are provided, edit is a no-op (no audit)."""
        OrderOfferService.edit_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
        )

        self.assertFalse(AuditLog.objects.filter(action="orders.offer.edited").exists())


class EditOfferValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.other_actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        self.offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )

    def test_non_owner_denied(self):
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=self.other_actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("600000.00"),
            )
        self.assertIn("original submitter", str(ctx.exception))

    def test_null_actor_denied(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=None,
                tenant_id=self.tenant.id,
                price_amount=Decimal("600000.00"),
            )

    def test_withdrawn_offer_cannot_be_edited(self):
        OrderOfferService.withdraw_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
        )
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("600000.00"),
            )
        self.assertIn("cannot be edited", str(ctx.exception).lower())

    def test_invalid_price_rejected(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("0.00"),
            )

    def test_cross_tenant_denied(self):
        other_tenant = make_tenant("other")
        with self.assertRaises(OrderOfferError):
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=other_tenant.id,
                price_amount=Decimal("600000.00"),
            )

    def test_order_no_longer_new_prevents_edit(self):
        self.order.status = OrderStatus.WAITING_SERVICE
        self.order.save()
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("600000.00"),
            )
        self.assertIn("no longer accepting", str(ctx.exception))


class WithdrawOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        self.offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )

    def test_successful_withdrawal(self):
        withdrawn = OrderOfferService.withdraw_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
        )

        self.assertEqual(withdrawn.status, OrderOfferStatus.WITHDRAWN)
        self.assertTrue(withdrawn.is_terminal)

    def test_withdrawal_records_audit(self):
        OrderOfferService.withdraw_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action="orders.offer.withdrawn",
                resource_id=self.offer.id,
            ).exists()
        )


class WithdrawOfferValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.other_actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        self.offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )

    def test_non_owner_denied(self):
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.withdraw_offer(
                offer_id=self.offer.id,
                actor=self.other_actor,
                tenant_id=self.tenant.id,
            )
        self.assertIn("original submitter", str(ctx.exception))

    def test_null_actor_denied(self):
        with self.assertRaises(OrderOfferError):
            OrderOfferService.withdraw_offer(
                offer_id=self.offer.id,
                actor=None,
                tenant_id=self.tenant.id,
            )

    def test_already_withdrawn_raises_domain_error(self):
        OrderOfferService.withdraw_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
        )
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.withdraw_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
            )
        self.assertIn("cannot be withdrawn", str(ctx.exception).lower())

    def test_cross_tenant_denied(self):
        other_tenant = make_tenant("other")
        with self.assertRaises(OrderOfferError):
            OrderOfferService.withdraw_offer(
                offer_id=self.offer.id,
                actor=self.other_actor,
                tenant_id=other_tenant.id,
            )

    def test_nonexistent_offer_raises_not_found(self):
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.withdraw_offer(
                offer_id=uuid.uuid4(),
                actor=self.actor,
                tenant_id=self.tenant.id,
            )
        self.assertIn("not found", str(ctx.exception))
