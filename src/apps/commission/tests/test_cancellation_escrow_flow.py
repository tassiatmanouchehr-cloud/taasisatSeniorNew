"""Financial Core PR-B: CancellationEscrowService — cancellation-before-
release safe behavior (Section 17), and RefundInstructionService.initiate()
against the Fake provider adapter (Section 16)."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.release_instruction import RefundInstruction, RefundInstructionStatus
from apps.commission.services.cancellation_escrow_service import CancellationEscrowService
from apps.commission.services.refund_instruction_service import RefundInstructionService
from apps.finance.models import EscrowRecord, EscrowStatus
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class CancellationEscrowFlowTest(CommissionTestCase):
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

    def _assign_and_pay(self):
        from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
        from apps.payments.models import PaymentIntent

        order = self._make_order()
        supplier = self._make_independent_supplier()
        assignment = AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        _deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        intent = PaymentIntent.objects.get(tenant_id=self.tenant.id, reference_type="Order", reference_id=order.id)
        attempt = PaymentIntentService.start_attempt(intent_id=intent.id)
        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference,
            payload={
                "provider_reference": attempt.provider_reference,
                "provider_event_id": "evt-1",
                "status": "SUCCEEDED",
                "amount": str(intent.amount),
                "currency": intent.currency,
            },
        )
        return order, assignment

    def test_paid_cancellation_creates_full_refund_instruction(self):
        order, _assignment = self._assign_and_pay()
        escrow = EscrowRecord.objects.get(tenant_id=self.tenant.id, order=order, status=EscrowStatus.HELD)

        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)

        instruction = RefundInstruction.objects.get(tenant_id=self.tenant.id, escrow=escrow)
        self.assertEqual(instruction.amount_irr, 10000000)
        self.assertEqual(instruction.status, RefundInstructionStatus.PENDING)

        escrow.refresh_from_db()
        self.assertEqual(escrow.remaining_amount_irr, 0)
        self.assertEqual(escrow.refunded_amount_irr, 10000000)

    def test_unpaid_cancellation_creates_no_escrow_movement(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        # No callback — the order was never paid.
        result = CancellationEscrowService.handle_cancellation(order=order, actor=self.actor)
        self.assertIsNone(result)
        self.assertFalse(EscrowRecord.objects.filter(tenant_id=self.tenant.id, order=order).exists())

    def test_duplicate_cancellation_is_idempotent(self):
        order, _assignment = self._assign_and_pay()
        escrow = EscrowRecord.objects.get(tenant_id=self.tenant.id, order=order, status=EscrowStatus.HELD)

        first = CancellationEscrowService.handle_cancellation(order=order, actor=self.actor)
        self.assertIsNotNone(first)
        # After the first call the Escrow leaves OPEN_ESCROW_STATUSES
        # (fully refunded), so a second call is a harmless no-op — not a
        # second RefundInstruction for the same money.
        second = CancellationEscrowService.handle_cancellation(order=order, actor=self.actor)
        self.assertIsNone(second)

        self.assertEqual(RefundInstruction.objects.filter(tenant_id=self.tenant.id, escrow=escrow).count(), 1)

    def test_manual_review_when_dispute_release_disabled(self):
        from apps.commission.services.configuration import DISPUTE_RELEASE_ENABLED_KEY

        order, _assignment = self._assign_and_pay()
        # Disable the gate this specific test needs off, after payment succeeded.
        self._enable_bool_config(DISPUTE_RELEASE_ENABLED_KEY, tenant=self.tenant)
        from apps.kernel.models.configuration import ConfigurationValue

        ConfigurationValue.objects.filter(
            tenant_id=self.tenant.id,
            config_key__key=DISPUTE_RELEASE_ENABLED_KEY,
        ).update(value=False)

        result = CancellationEscrowService.handle_cancellation(order=order, actor=self.actor)
        self.assertIsNone(result)
        self.assertFalse(RefundInstruction.objects.filter(tenant_id=self.tenant.id, order=order).exists())

    def test_refund_instruction_initiate_completes_via_fake_provider(self):
        order, _assignment = self._assign_and_pay()
        escrow = EscrowRecord.objects.get(tenant_id=self.tenant.id, order=order, status=EscrowStatus.HELD)

        instruction = RefundInstructionService.create(
            escrow=escrow,
            order=order,
            invoice=escrow.source_document,
            amount_irr=10000000,
            source="MANUAL",
            reason="test",
            idempotency_key="refund-init-1",
        )
        completed = RefundInstructionService.initiate(refund_instruction_id=instruction.id)

        self.assertEqual(completed.status, RefundInstructionStatus.COMPLETED)
        self.assertTrue(completed.psp_reference.startswith("FAKE-REFUND-"))
        self.assertIsNotNone(completed.completed_at)
