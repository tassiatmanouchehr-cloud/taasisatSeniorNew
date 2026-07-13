"""Financial Core PR-B: EscrowIntegrationService — a callback for a
superseded assignment cycle's PaymentIntent must never revive it (Section
2's "callback after deadline expiry must not revive an expired assignment"
and "old PaymentIntent non-actionable after expiry"). Exercises the
PaymentDeadline-by-exact-id lookup directly, since driving a real stale
callback end-to-end through PaymentCallbackService would require the
provider to accept a callback for an already-cancelled PaymentIntent, which
apps.payments' own state machine already refuses independently of PR-B."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
from apps.commission.services.errors import PreServicePaymentError
from apps.commission.services.escrow_integration_service import EscrowIntegrationService
from apps.finance.models import EscrowRecord
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.models import PaymentIntent

from .helpers import CommissionTestCase


class EscrowIntegrationStaleCycleTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self._enable_all_financial_core_pr_b_gates()
        self._seed_fixed_pricing_rule(amount="10000000")
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(
            self.tenant,
            self.actor,
            [
                "booking.assignment.assign",
                "booking.assignment.cancel",
            ],
        )

    def test_stale_deadline_rejects_hold_and_creates_no_escrow(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        old_deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        old_intent = PaymentIntent.objects.get(
            tenant_id=self.tenant.id,
            reference_type="Order",
            reference_id=order.id,
        )

        # Supersede the cycle: cancelling the assignment cancels the
        # PaymentDeadline via AssignmentService._cancel_financial_core_deadline().
        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)
        old_deadline.refresh_from_db()
        self.assertEqual(old_deadline.status, PaymentDeadlineStatus.CANCELLED)

        with self.assertRaises(PreServicePaymentError):
            EscrowIntegrationService.handle_preservice_payment_succeeded(
                intent=old_intent,
                payment_transaction=None,
            )

        self.assertFalse(EscrowRecord.objects.filter(tenant_id=self.tenant.id, order=order).exists())

    def test_new_assignment_cycle_gets_a_new_deadline_and_intent(self):
        order = self._make_order()
        supplier_a = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier_a, assigned_by=self.actor)
        first_deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        first_intent = PaymentIntent.objects.get(
            tenant_id=self.tenant.id,
            reference_type="Order",
            reference_id=order.id,
        )

        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)

        supplier_b = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier_b, assigned_by=self.actor)
        second_deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        second_intent = PaymentIntent.objects.get(
            tenant_id=self.tenant.id,
            reference_type="Order",
            reference_id=order.id,
            metadata__payment_deadline_id=str(second_deadline.id),
        )

        self.assertNotEqual(first_deadline.id, second_deadline.id)
        self.assertNotEqual(first_intent.id, second_intent.id)
        self.assertEqual(second_intent.metadata["payment_deadline_id"], str(second_deadline.id))
