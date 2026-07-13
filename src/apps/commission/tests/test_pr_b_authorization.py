"""Financial Core PR-B: authorization adversarial matrix (Section 21) —
resource-scoped, not merely tenant-role-scoped. A customer may only act on
their own order; a provider/caregiver may never approve completion, open a
dispute in the customer's name, or resolve a dispute; platform-only actions
require the dedicated permission keys."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.objection import ObjectionPeriod, ObjectionPeriodStatus
from apps.commission.services.dispute_service import DisputeService
from apps.commission.services.errors import DisputeError, ObjectionPeriodError
from apps.commission.services.objection_service import ObjectionPeriodService
from apps.execution.services.session_service import ExecutionService
from apps.finance.services import FinancialPartyService
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import CommissionTestCase


class PrBAuthorizationTest(CommissionTestCase):
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
                "execution.session.close",
            ],
        )

    def _completed_order_with_open_objection(self):
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

        objection = ObjectionPeriod.objects.get(tenant_id=self.tenant.id, order=order)
        return order, objection

    def test_provider_cannot_approve_customer_completion(self):

        order, objection = self._completed_order_with_open_objection()
        provider_person_user = make_actor(self.tenant, full_name="Provider")

        with self.assertRaises(ObjectionPeriodError):
            ObjectionPeriodService.approve_by_customer(objection_period_id=objection.id, actor=provider_person_user)

        objection.refresh_from_db()
        self.assertEqual(objection.status, ObjectionPeriodStatus.OPEN)

    def test_another_customer_cannot_approve_this_order(self):
        from apps.kernel.models import UserAccount

        order, objection = self._completed_order_with_open_objection()
        other_customer = self._create_customer(tenant=self.tenant)
        other_user = UserAccount.objects.get(id=other_customer.user_id)

        with self.assertRaises(ObjectionPeriodError):
            ObjectionPeriodService.approve_by_customer(objection_period_id=objection.id, actor=other_user)

    def test_cross_tenant_customer_cannot_approve(self):
        from apps.kernel.models import UserAccount

        order, objection = self._completed_order_with_open_objection()
        cross_tenant_customer = self._create_customer(tenant=self.other_tenant)
        cross_tenant_user = UserAccount.objects.get(id=cross_tenant_customer.user_id)

        with self.assertRaises(ObjectionPeriodError):
            ObjectionPeriodService.approve_by_customer(objection_period_id=objection.id, actor=cross_tenant_user)

    def test_none_actor_cannot_approve(self):
        _order, objection = self._completed_order_with_open_objection()

        with self.assertRaises(ObjectionPeriodError):
            ObjectionPeriodService.approve_by_customer(objection_period_id=objection.id, actor=None)

    def test_provider_cannot_open_dispute_as_customer(self):
        order, _objection = self._completed_order_with_open_objection()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)
        provider_user = make_actor(self.tenant, full_name="Provider")

        with self.assertRaises(DisputeError):
            DisputeService.open(
                order=order,
                customer_party=customer_party,
                disputed_amount_irr=100000,
                reason_code="OTHER",
                actor=provider_user,
            )

    def test_none_actor_cannot_open_dispute(self):
        order, _objection = self._completed_order_with_open_objection()
        customer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)

        with self.assertRaises(DisputeError):
            DisputeService.open(
                order=order,
                customer_party=customer_party,
                disputed_amount_irr=100000,
                reason_code="OTHER",
                actor=None,
            )
