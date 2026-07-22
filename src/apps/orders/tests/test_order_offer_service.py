"""
Tests for OrderOfferService -- Sprint 5.1: Submission Lifecycle Foundation.

Covers: submit_offer(), edit_offer(), withdraw_offer() -- authorization,
actor-to-supplier identity, tenant isolation, state validation, concurrency,
audit, domain errors.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.kernel.models.audit import AuditLog
from apps.orders.models import OrderOfferStatus, OrderStatus
from apps.orders.services.order_offer_service import OrderOfferError, OrderOfferService

from .helpers import grant_permissions, make_order, make_supplier, make_tenant, make_user

# The permission key required by submit_offer()
_SUBMIT_PERMISSION = "orders.offer.submit"


class SubmitOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_successful_submission(self, mock_resolve):
        mock_resolve.return_value = self.supplier

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
        self.assertEqual(offer.submitted_by_id, self.actor.id)

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_submission_records_audit_without_free_text(self, mock_resolve):
        mock_resolve.return_value = self.supplier

        offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
            terms="Confidential terms here",
            message="Private message",
        )

        audit = AuditLog.objects.get(
            tenant_id=self.tenant.id,
            action="orders.offer.submitted",
        )
        self.assertEqual(audit.resource_id, offer.id)
        # Verify no free-form text in audit payload
        self.assertNotIn("Confidential", str(audit.after_snapshot))
        self.assertNotIn("Private", str(audit.after_snapshot))

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_submission_with_optional_fields(self, mock_resolve):
        mock_resolve.return_value = self.supplier

        offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("750000.00"),
            currency="USD",
            estimated_duration_minutes=120,
            terms="Net 30",
            message="Hello",
        )

        self.assertEqual(offer.currency, "USD")
        self.assertEqual(offer.estimated_duration_minutes, 120)
        self.assertEqual(offer.terms, "Net 30")
        self.assertEqual(offer.message, "Hello")


class SubmitOfferActorSupplierAuthorizationTest(TestCase):
    """Tests that the actor must own the supplier identity they submit for."""

    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.own_supplier = make_supplier(self.tenant)
        self.other_supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_actor_submits_for_own_supplier_succeeds(self, mock_resolve):
        mock_resolve.return_value = self.own_supplier

        offer = OrderOfferService.submit_offer(
            order_id=self.order.id,
            supplier_id=self.own_supplier.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("500000.00"),
        )

        self.assertEqual(offer.supplier_id, self.own_supplier.id)

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_actor_submits_for_another_supplier_same_tenant_denied(self, mock_resolve):
        """A permitted actor cannot submit on behalf of a different supplier."""
        mock_resolve.return_value = self.own_supplier  # actor's OWN supplier

        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.other_supplier.id,  # NOT the actor's supplier
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("not authorized", str(ctx.exception))

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_actor_with_no_provider_profile_denied(self, mock_resolve):
        from apps.accounts.services.errors import AccountsError

        mock_resolve.side_effect = AccountsError("No provider profile")

        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.own_supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("no active supplier identity", str(ctx.exception))

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_actor_with_inactive_profile_denied(self, mock_resolve):
        from apps.accounts.services.errors import AccountsError

        mock_resolve.side_effect = AccountsError("Profile not activated")

        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.own_supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("no active supplier identity", str(ctx.exception))

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_cross_tenant_supplier_impersonation_denied(self, mock_resolve):
        """Actor in tenant A cannot use a supplier_id from tenant B."""
        other_tenant = make_tenant("other")
        cross_supplier = make_supplier(other_tenant)
        mock_resolve.return_value = self.own_supplier

        with self.assertRaises(OrderOfferError):
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=cross_supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )


class SubmitOfferValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

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

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_order_not_in_new_status_rejected(self, mock_resolve):
        mock_resolve.return_value = self.supplier
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

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_zero_price_rejected(self, mock_resolve):
        mock_resolve.return_value = self.supplier

        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("0.00"),
            )
        self.assertIn("positive", str(ctx.exception))

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_duplicate_submission_raises_domain_error(self, mock_resolve):
        mock_resolve.return_value = self.supplier

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

    def test_cross_tenant_order_not_found(self):
        other_tenant = make_tenant("other")
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=other_tenant.id,
                price_amount=Decimal("500000.00"),
            )
        self.assertIn("not found", str(ctx.exception))


class SubmitOfferPermissionTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        # Permission granted -- this test verifies PermissionService.require() is CALLED,
        # not that it denies. The mock replaces the real call.
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

    @patch("apps.orders.services.order_offer_service.resolve_supplier_for_user")
    def test_permission_service_is_called(self, mock_resolve):
        mock_resolve.return_value = self.supplier

        with patch("apps.orders.services.order_offer_service.PermissionService.require") as mock_require:
            OrderOfferService.submit_offer(
                order_id=self.order.id,
                supplier_id=self.supplier.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
                price_amount=Decimal("500000.00"),
            )

        mock_require.assert_called_once()
        call_args = mock_require.call_args
        self.assertEqual(call_args[0][1], "orders.offer.submit")


class EditOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

        with patch("apps.orders.services.order_offer_service.resolve_supplier_for_user") as mock:
            mock.return_value = self.supplier
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

    def test_edit_records_audit_without_free_text(self):
        OrderOfferService.edit_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
            price_amount=Decimal("600000.00"),
            terms="Secret new terms",
        )

        audit = AuditLog.objects.get(action="orders.offer.edited")
        # Verify no free-form text content in audit
        self.assertNotIn("Secret", str(audit.after_snapshot))
        # Verify changed_fields is recorded
        self.assertIn("price_amount", audit.after_snapshot.get("changed_fields", []))
        self.assertIn("terms", audit.after_snapshot.get("changed_fields", []))

    def test_no_change_is_noop(self):
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
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

        with patch("apps.orders.services.order_offer_service.resolve_supplier_for_user") as mock:
            mock.return_value = self.supplier
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

    def test_withdrawn_offer_cannot_be_edited(self):
        OrderOfferService.withdraw_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
        )
        with self.assertRaises(OrderOfferError):
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
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

    def test_cross_tenant_denied(self):
        other_tenant = make_tenant("other")
        with self.assertRaises(OrderOfferError):
            OrderOfferService.edit_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=other_tenant.id,
                price_amount=Decimal("600000.00"),
            )


class WithdrawOfferHappyPathTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

        with patch("apps.orders.services.order_offer_service.resolve_supplier_for_user") as mock:
            mock.return_value = self.supplier
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

        audit = AuditLog.objects.get(action="orders.offer.withdrawn")
        self.assertEqual(audit.resource_id, self.offer.id)


class WithdrawOfferValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_user(self.tenant)
        self.other_actor = make_user(self.tenant)
        self.supplier = make_supplier(self.tenant)
        self.order = make_order(self.tenant, status=OrderStatus.NEW)
        grant_permissions(self.tenant, self.actor, [_SUBMIT_PERMISSION])

        with patch("apps.orders.services.order_offer_service.resolve_supplier_for_user") as mock:
            mock.return_value = self.supplier
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

    def test_already_withdrawn_raises_domain_error(self):
        OrderOfferService.withdraw_offer(
            offer_id=self.offer.id,
            actor=self.actor,
            tenant_id=self.tenant.id,
        )
        with self.assertRaises(OrderOfferError):
            OrderOfferService.withdraw_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
            )

    def test_order_no_longer_new_prevents_withdrawal(self):
        self.order.status = OrderStatus.WAITING_SERVICE
        self.order.save()
        with self.assertRaises(OrderOfferError) as ctx:
            OrderOfferService.withdraw_offer(
                offer_id=self.offer.id,
                actor=self.actor,
                tenant_id=self.tenant.id,
            )
        self.assertIn("no longer accepting", str(ctx.exception))

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


class IntegrityErrorHandlingTest(TestCase):
    """Verify that only the duplicate-offer constraint is caught; unrelated
    IntegrityError cases propagate normally."""

    def test_unrelated_integrity_error_not_swallowed(self):
        """An IntegrityError that does NOT match the duplicate-offer constraint
        must propagate, not be caught as a duplicate-offer error."""
        # _is_duplicate_offer_violation should return False for unrelated errors
        from django.db import IntegrityError as DjIntegrityError

        from apps.orders.services.order_offer_service import OrderOfferService

        unrelated = DjIntegrityError("some_other_constraint_violation")
        self.assertFalse(OrderOfferService._is_duplicate_offer_violation(unrelated))

        # The actual duplicate constraint name should match
        duplicate = DjIntegrityError('duplicate key value violates unique constraint "uq_order_offer_one_per_supplier"')
        self.assertTrue(OrderOfferService._is_duplicate_offer_violation(duplicate))
