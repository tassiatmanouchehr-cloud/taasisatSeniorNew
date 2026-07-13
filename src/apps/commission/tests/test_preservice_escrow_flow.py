"""Financial Core PR-B: the full end-to-end pre-service payment -> Escrow
hold -> execution -> objection period -> customer approval -> release
instruction flow, with every gate explicitly enabled. Section 28's primary
integration scenario — narrower unit tests for each service live in their
own test modules alongside this one."""

import uuid

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
from apps.commission.models.objection import ObjectionPeriod, ObjectionPeriodStatus
from apps.commission.models.release_instruction import ReleaseInstruction, ReleaseInstructionStatus
from apps.commission.services.objection_service import ObjectionPeriodService
from apps.commission.services.reconciliation_service import EscrowReconciliationService
from apps.execution.services.session_service import ExecutionService
from apps.finance.models import EscrowRecord, EscrowStatus
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class PreServiceEscrowFlowTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self._enable_all_financial_core_pr_b_gates()
        self._seed_fixed_pricing_rule(amount="10000000")
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, self.actor, ["booking.assignment.assign"])

    def _assign_and_pay(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        assignment = AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        from apps.payments.models import PaymentIntent

        intent = PaymentIntent.objects.get(tenant_id=self.tenant.id, reference_type="Order", reference_id=order.id)
        self.assertEqual(intent.metadata["financial_core_flow"], "preservice")
        self.assertEqual(intent.metadata["payment_deadline_id"], str(deadline.id))
        self.assertEqual(intent.amount, 10000000)

        attempt = PaymentIntentService.start_attempt(intent_id=intent.id)
        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference,
            payload={
                "provider_reference": attempt.provider_reference,
                "provider_event_id": str(uuid.uuid4()),
                "status": "SUCCEEDED",
                "amount": str(intent.amount),
                "currency": intent.currency,
            },
        )

        deadline.refresh_from_db()
        self.assertEqual(deadline.status, PaymentDeadlineStatus.COMPLETED)

        escrow = EscrowRecord.objects.get(tenant_id=self.tenant.id, order=order)
        self.assertEqual(escrow.status, EscrowStatus.HELD)
        self.assertEqual(escrow.original_amount_irr, 10000000)
        self.assertEqual(escrow.remaining_amount_irr, 10000000)
        self.assertEqual(escrow.held_amount_irr, 10000000)
        self.assertEqual(escrow.blocked_amount_irr, 0)
        self.assertEqual(escrow.released_amount_irr, 0)

        return order, supplier, assignment, escrow

    def test_full_flow_undisputed_customer_approval(self):
        order, _supplier, assignment, escrow = self._assign_and_pay()

        session = ExecutionService.create_session(supplier_assignment=assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        ExecutionService.close_session(session_id=session.id)

        objection = ObjectionPeriod.objects.get(tenant_id=self.tenant.id, order=order)
        self.assertEqual(objection.status, ObjectionPeriodStatus.OPEN)
        self.assertIsNotNone(objection.auto_approve_job_id)

        customer_user = self._customer_user_for_order(order)
        ObjectionPeriodService.approve_by_customer(objection_period_id=objection.id, actor=customer_user)

        objection.refresh_from_db()
        self.assertEqual(objection.status, ObjectionPeriodStatus.CUSTOMER_APPROVED)

        escrow.refresh_from_db()
        self.assertEqual(escrow.remaining_amount_irr, 0)
        self.assertEqual(escrow.released_amount_irr, 10000000)
        self.assertEqual(escrow.status, EscrowStatus.FULLY_RELEASED)

        instruction = ReleaseInstruction.objects.get(tenant_id=self.tenant.id, escrow=escrow)
        self.assertEqual(instruction.gross_releasable_amount_irr, 10000000)
        self.assertEqual(instruction.status, ReleaseInstructionStatus.READY)
        self.assertEqual(instruction.source, "CUSTOMER_APPROVAL")

        result = EscrowReconciliationService.check_escrow(escrow_id=escrow.id)
        self.assertTrue(result.ok, result.discrepancies)

    def test_execution_cannot_start_without_held_escrow(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        assignment = AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        # Payment never happens — no callback, no Escrow.
        session = ExecutionService.create_session(supplier_assignment=assignment)
        from apps.execution.services.session_service import ExecutionError

        with self.assertRaises(ExecutionError):
            ExecutionService.start_session(session_id=session.id)

    def test_duplicate_callback_is_idempotent_single_escrow(self):
        order, _supplier, _assignment, escrow = self._assign_and_pay()

        from apps.payments.models import PaymentAttempt

        attempt = PaymentAttempt.objects.get(intent__reference_id=order.id)
        # Re-sending the exact same accepted callback (same provider_event_id
        # the service already recorded) must be a pure idempotent replay.
        from apps.payments.models import PaymentCallback

        callback = PaymentCallback.objects.get(attempt=attempt)
        PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference,
            payload={
                "provider_reference": attempt.provider_reference,
                "provider_event_id": callback.provider_event_id,
                "status": "SUCCEEDED",
                "amount": str(attempt.intent.amount),
                "currency": attempt.intent.currency,
            },
        )

        self.assertEqual(EscrowRecord.objects.filter(tenant_id=self.tenant.id, order=order).count(), 1)
        escrow.refresh_from_db()
        self.assertEqual(escrow.original_amount_irr, 10000000)
