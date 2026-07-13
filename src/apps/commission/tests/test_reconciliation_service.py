"""Financial Core PR-B: EscrowReconciliationService — happy-path invariant
checks, and a real, deliberately-manufactured discrepancy (a Dispute whose
blocked amount diverges from the Escrow's own blocked_amount_irr, bypassing
DisputeService so the read-only reconciliation service has something real
to catch rather than something it invented itself). Section 25: the service
must report discrepancies explicitly, never auto-correct."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.dispute import Dispute, DisputeReasonCode, DisputeStatus
from apps.commission.services.reconciliation_service import EscrowReconciliationService
from apps.finance.models import EscrowRecord, EscrowStatus
from apps.finance.services import FinancialPartyService
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class ReconciliationServiceTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self._enable_all_financial_core_pr_b_gates()
        self._seed_fixed_pricing_rule(amount="10000000")
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, self.actor, ["booking.assignment.assign"])

    def _paid_order(self):
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
        return order, escrow

    def test_freshly_held_escrow_reconciles_clean(self):
        _order, escrow = self._paid_order()
        result = EscrowReconciliationService.check_escrow(escrow_id=escrow.id)
        self.assertTrue(result.ok, result.discrepancies)
        self.assertEqual(result.discrepancies, [])

    def test_check_tenant_covers_every_escrow(self):
        self._paid_order()
        self._paid_order()
        results = EscrowReconciliationService.check_tenant(tenant_id=self.tenant.id)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.ok for r in results))

    def test_detects_open_dispute_total_mismatch(self):
        order, escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)

        # Deliberately bypass DisputeService/EscrowService: create a Dispute
        # row directly so its disputed_amount_irr diverges from the
        # Escrow's own blocked_amount_irr (which stays 0) — a real
        # inconsistency the read-only reconciliation service must report,
        # not something it invents on its own.
        Dispute.objects.create(
            tenant_id=self.tenant.id,
            order=order,
            invoice=escrow.source_document,
            escrow=escrow,
            customer_party=customer_party,
            disputed_amount_irr=500000,
            reason_code=DisputeReasonCode.OTHER,
            status=DisputeStatus.OPEN,
            opened_by=customer_user,
        )

        result = EscrowReconciliationService.check_escrow(escrow_id=escrow.id)
        self.assertFalse(result.ok)
        self.assertTrue(any("open dispute total" in d for d in result.discrepancies))

    def test_reconciliation_does_not_mutate_state(self):
        order, escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)
        Dispute.objects.create(
            tenant_id=self.tenant.id,
            order=order,
            invoice=escrow.source_document,
            escrow=escrow,
            customer_party=customer_party,
            disputed_amount_irr=500000,
            reason_code=DisputeReasonCode.OTHER,
            status=DisputeStatus.OPEN,
            opened_by=customer_user,
        )

        before = (escrow.blocked_amount_irr, escrow.remaining_amount_irr, escrow.status)
        EscrowReconciliationService.check_escrow(escrow_id=escrow.id)
        escrow.refresh_from_db()
        after = (escrow.blocked_amount_irr, escrow.remaining_amount_irr, escrow.status)
        self.assertEqual(before, after)
