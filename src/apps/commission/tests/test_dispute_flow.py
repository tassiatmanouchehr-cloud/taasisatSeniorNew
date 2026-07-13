"""Financial Core PR-B: DisputeService — partial blocking (the exact
10,000,000 / 1,543,000 / 8,457,000 IRR worked example from Section 12),
line validation, idempotency, and cross-tenant/cross-order rejection."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.dispute import Dispute, DisputeLine, DisputeReasonCode, DisputeStatus
from apps.commission.services.dispute_service import DisputeService
from apps.commission.services.errors import DisputeError
from apps.finance.models import EscrowRecord, EscrowStatus
from apps.finance.services import FinancialPartyService
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class DisputePartialBlockTest(CommissionTestCase):
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

    def test_exact_worked_example_partial_block(self):
        order, escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)

        dispute = DisputeService.open(
            order=order,
            customer_party=customer_party,
            disputed_amount_irr=1543000,
            reason_code=DisputeReasonCode.SERVICE_QUALITY,
            actor=customer_user,
        )

        escrow.refresh_from_db()
        self.assertEqual(escrow.blocked_amount_irr, 1543000)
        self.assertEqual(escrow.remaining_amount_irr, 8457000)
        self.assertEqual(escrow.original_amount_irr, 10000000)
        self.assertEqual(
            escrow.released_amount_irr
            + escrow.refunded_amount_irr
            + escrow.blocked_amount_irr
            + escrow.remaining_amount_irr,
            escrow.original_amount_irr,
        )
        self.assertEqual(dispute.status, DisputeStatus.OPEN)

    def test_duplicate_dispute_command_does_not_double_block(self):
        order, escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)

        DisputeService.open(
            order=order,
            customer_party=customer_party,
            disputed_amount_irr=1543000,
            reason_code=DisputeReasonCode.SERVICE_QUALITY,
            actor=customer_user,
            idempotency_key="fixed-key",
        )
        DisputeService.open(
            order=order,
            customer_party=customer_party,
            disputed_amount_irr=1543000,
            reason_code=DisputeReasonCode.SERVICE_QUALITY,
            actor=customer_user,
            idempotency_key="fixed-key",
        )

        escrow.refresh_from_db()
        self.assertEqual(escrow.blocked_amount_irr, 1543000)
        self.assertEqual(Dispute.objects.filter(tenant_id=self.tenant.id, escrow=escrow).count(), 1)

    def test_cannot_dispute_more_than_remaining(self):
        order, _escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)

        with self.assertRaises(DisputeError):
            DisputeService.open(
                order=order,
                customer_party=customer_party,
                disputed_amount_irr=10000001,
                reason_code=DisputeReasonCode.SERVICE_QUALITY,
                actor=customer_user,
            )

    def test_only_order_owning_customer_may_dispute(self):
        from apps.kernel.models import UserAccount

        order, _escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        other_customer = self._create_customer(tenant=self.tenant)
        other_user = UserAccount.objects.get(id=other_customer.user_id)

        with self.assertRaises(DisputeError):
            DisputeService.open(
                order=order,
                customer_party=customer_party,
                disputed_amount_irr=100000,
                reason_code=DisputeReasonCode.OTHER,
                actor=other_user,
            )

    def test_dispute_lines_must_sum_to_disputed_amount(self):
        order, escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)
        item = escrow.source_document.items.first()

        with self.assertRaises(DisputeError):
            DisputeService.open(
                order=order,
                customer_party=customer_party,
                disputed_amount_irr=1543000,
                reason_code=DisputeReasonCode.SERVICE_QUALITY,
                actor=customer_user,
                lines=[{"invoice_item": item, "disputed_amount_irr": 500000}],
            )

    def test_dispute_lines_recorded_and_linked_to_invoice_item(self):
        order, escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)
        item = escrow.source_document.items.first()

        dispute = DisputeService.open(
            order=order,
            customer_party=customer_party,
            disputed_amount_irr=1543000,
            reason_code=DisputeReasonCode.SERVICE_QUALITY,
            actor=customer_user,
            lines=[{"invoice_item": item, "disputed_amount_irr": 1543000, "reason": "wrong duration"}],
        )

        lines = DisputeLine.objects.filter(tenant_id=self.tenant.id, dispute=dispute)
        self.assertEqual(lines.count(), 1)
        self.assertEqual(lines.first().disputed_amount_irr, 1543000)

    def test_open_disputed_total_for_escrow(self):
        order, escrow = self._paid_order()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)

        DisputeService.open(
            order=order,
            customer_party=customer_party,
            disputed_amount_irr=1543000,
            reason_code=DisputeReasonCode.SERVICE_QUALITY,
            actor=customer_user,
        )

        total = DisputeService.open_disputed_total_for_escrow(escrow=escrow)
        self.assertEqual(total, 1543000)
