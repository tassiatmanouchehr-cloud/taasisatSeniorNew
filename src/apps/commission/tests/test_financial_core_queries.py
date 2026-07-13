"""Financial Core PR-B: FinancialCoreQueryService — the read-only service
every portal's minimal UI (Section 24) consumes. Sanity-checks the
ViewModel assembly against a real held/disputed/released Escrow."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.dispute import DisputeReasonCode
from apps.commission.services.dispute_service import DisputeService
from apps.commission.services.queries import FinancialCoreQueryService
from apps.execution.services.session_service import ExecutionService
from apps.finance.models import EscrowRecord, EscrowStatus
from apps.finance.services import FinancialPartyService
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class FinancialCoreQueryServiceTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self._enable_all_financial_core_pr_b_gates()
        self._seed_fixed_pricing_rule(amount="10000000")
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, self.actor, ["booking.assignment.assign", "execution.session.close"])

    def test_legacy_tenant_returns_disabled_view(self):
        from apps.kernel.models import Tenant

        legacy_tenant = Tenant.objects.create(slug="legacy-tenant-x", name="Legacy")
        order = self._make_order(tenant=legacy_tenant)
        view = FinancialCoreQueryService.get_order_financial_view(tenant_id=legacy_tenant.id, order=order)
        self.assertFalse(view.preservice_payment_enabled)
        self.assertFalse(view.escrow_exists)

    def test_order_financial_view_reflects_held_escrow_and_open_objection(self):
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

        session = ExecutionService.create_session(supplier_assignment=assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        ExecutionService.close_session(session_id=session.id, changed_by=self.actor)

        view = FinancialCoreQueryService.get_order_financial_view(tenant_id=self.tenant.id, order=order)
        self.assertTrue(view.escrow_exists)
        self.assertEqual(view.escrow_status, EscrowStatus.HELD)
        self.assertEqual(view.original_amount_irr, 10000000)
        self.assertTrue(view.objection_exists)
        self.assertTrue(view.can_customer_approve)
        self.assertTrue(view.can_customer_dispute)

        escrow = EscrowRecord.objects.get(tenant_id=self.tenant.id, order=order)
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        customer_user = self._customer_user_for_order(order)
        DisputeService.open(
            order=order,
            customer_party=customer_party,
            disputed_amount_irr=1543000,
            reason_code=DisputeReasonCode.SERVICE_QUALITY,
            actor=customer_user,
        )

        view2 = FinancialCoreQueryService.get_order_financial_view(tenant_id=self.tenant.id, order=order)
        self.assertEqual(len(view2.disputes), 1)
        self.assertEqual(view2.disputes[0].disputed_amount_irr, 1543000)
        self.assertEqual(view2.blocked_amount_irr, 1543000)

        escrows = FinancialCoreQueryService.list_escrows_for_tenant(tenant_id=self.tenant.id)
        self.assertEqual(len(escrows), 1)

        detail = FinancialCoreQueryService.get_escrow_detail(tenant_id=self.tenant.id, escrow_id=escrow.id)
        self.assertIsNotNone(detail)
        self.assertGreaterEqual(len(detail.movements), 2)
        self.assertEqual(len(detail.disputes), 1)

        disputes = FinancialCoreQueryService.list_disputes_for_tenant(tenant_id=self.tenant.id)
        self.assertEqual(len(disputes), 1)

        gates = FinancialCoreQueryService.get_feature_gate_status(tenant_id=self.tenant.id)
        self.assertTrue(gates.preservice_payment_enabled)
        self.assertTrue(gates.dispute_release_enabled)
