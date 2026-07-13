"""Financial Core PR-B: DisputeResolutionService — allocation conservation,
release/refund instruction creation, idempotency, and platform-only
authorization (Sections 14-15, 21)."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.dispute import Dispute, DisputeReasonCode, DisputeStatus
from apps.commission.models.release_instruction import (
    ReleaseInstruction,
    ReleaseInstructionSource,
    ReleaseInstructionStatus,
)
from apps.commission.permission_keys import COMMISSION_DISPUTE_RESOLVE
from apps.commission.services.dispute_resolution_service import DisputeResolutionService
from apps.commission.services.dispute_service import DisputeService
from apps.commission.services.errors import DisputeError
from apps.finance.models import EscrowRecord, EscrowStatus
from apps.finance.services import FinancialPartyService
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class DisputeResolutionFlowTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self._enable_all_financial_core_pr_b_gates()
        self._seed_fixed_pricing_rule(amount="10000000")
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, self.actor, ["booking.assignment.assign"])
        self.platform_actor = make_actor(self.tenant, full_name="Platform Ops")
        grant_permissions(self.tenant, self.platform_actor, [COMMISSION_DISPUTE_RESOLVE])

    def _disputed_order(self, disputed_amount_irr=1543000):
        from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
        from apps.payments.models import PaymentIntent

        order = self._make_order()
        supplier = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

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
        escrow = EscrowRecord.objects.get(tenant_id=self.tenant.id, order=order, status=EscrowStatus.HELD)

        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)
        dispute = DisputeService.open(
            order=order,
            customer_party=customer_party,
            disputed_amount_irr=disputed_amount_irr,
            reason_code=DisputeReasonCode.SERVICE_QUALITY,
            actor=customer_user,
        )
        return order, escrow, dispute

    def test_full_refund_resolution_conserves_amount(self):
        order, escrow, dispute = self._disputed_order()

        resolution = DisputeResolutionService.resolve(
            dispute_id=dispute.id,
            reason="Service not performed",
            actor=self.platform_actor,
            idempotency_key="res-1",
            customer_refund_amount_irr=1543000,
        )

        self.assertEqual(
            resolution.customer_refund_amount_irr
            + resolution.platform_amount_irr
            + resolution.company_amount_irr
            + resolution.caregiver_amount_irr,
            resolution.total_blocked_amount_irr,
        )

        dispute.refresh_from_db()
        self.assertEqual(dispute.status, DisputeStatus.RESOLVED)
        self.assertEqual(dispute.resolution_type, "FULL_REFUND")

        escrow.refresh_from_db()
        self.assertEqual(escrow.blocked_amount_irr, 0)
        self.assertEqual(escrow.refunded_amount_irr, 1543000)
        self.assertEqual(
            escrow.released_amount_irr
            + escrow.refunded_amount_irr
            + escrow.blocked_amount_irr
            + escrow.remaining_amount_irr,
            escrow.original_amount_irr,
        )

    def test_mixed_resolution_creates_both_release_and_refund_instructions(self):
        order, escrow, dispute = self._disputed_order(disputed_amount_irr=1000000)

        DisputeResolutionService.resolve(
            dispute_id=dispute.id,
            reason="Partially valid claim",
            actor=self.platform_actor,
            idempotency_key="res-mixed",
            customer_refund_amount_irr=400000,
            platform_amount_irr=200000,
            company_amount_irr=200000,
            caregiver_amount_irr=200000,
        )

        dispute.refresh_from_db()
        self.assertEqual(dispute.resolution_type, "MIXED")

        release = ReleaseInstruction.objects.get(
            tenant_id=self.tenant.id,
            escrow=escrow,
            source=ReleaseInstructionSource.DISPUTE_RESOLUTION,
        )
        self.assertEqual(release.gross_releasable_amount_irr, 600000)
        self.assertEqual(release.status, ReleaseInstructionStatus.READY)

        from apps.commission.models.release_instruction import RefundInstruction

        refund = RefundInstruction.objects.get(tenant_id=self.tenant.id, escrow=escrow)
        self.assertEqual(refund.amount_irr, 400000)

    def test_resolution_allocation_must_sum_to_disputed_amount(self):
        _order, _escrow, dispute = self._disputed_order()

        with self.assertRaises(DisputeError):
            DisputeResolutionService.resolve(
                dispute_id=dispute.id,
                reason="bad math",
                actor=self.platform_actor,
                idempotency_key="res-bad",
                customer_refund_amount_irr=1000,
            )

    def test_resolution_is_idempotent(self):
        _order, _escrow, dispute = self._disputed_order()

        first = DisputeResolutionService.resolve(
            dispute_id=dispute.id,
            reason="x",
            actor=self.platform_actor,
            idempotency_key="res-idem",
            customer_refund_amount_irr=1543000,
        )
        second = DisputeResolutionService.resolve(
            dispute_id=dispute.id,
            reason="x",
            actor=self.platform_actor,
            idempotency_key="res-idem",
            customer_refund_amount_irr=1543000,
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(Dispute.objects.get(id=dispute.id).status, DisputeStatus.RESOLVED)

    def test_non_platform_actor_cannot_resolve_dispute(self):
        _order, _escrow, dispute = self._disputed_order()
        random_actor = make_actor(self.tenant, full_name="No Permission")

        with self.assertRaises(PermissionDenied):
            DisputeResolutionService.resolve(
                dispute_id=dispute.id,
                reason="x",
                actor=random_actor,
                idempotency_key="res-denied",
                customer_refund_amount_irr=1543000,
            )
