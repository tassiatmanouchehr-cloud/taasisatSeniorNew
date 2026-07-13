"""Financial Core PR-B: feature-gate / legacy-tenant safety (Section 18).
Every new PR-B gate defaults DISABLED — an existing tenant that never opts
in must see exactly the pre-PR-B behavior: no pre-service invoice/intent,
no Escrow, no objection period, no execution-start guard, no assertion
that money is held when it never was."""

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
from apps.commission.models.objection import ObjectionPeriod
from apps.commission.services.configuration import CommissionConfiguration
from apps.execution.services.session_service import ExecutionService
from apps.finance.models import EscrowRecord
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.payments.models import PaymentIntent

from .helpers import CommissionTestCase


class PrBFeatureGateDefaultsTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(
            self.tenant,
            self.actor,
            [
                "booking.assignment.assign",
                "execution.session.close",
            ],
        )

    def test_all_pr_b_gates_default_disabled(self):
        self.assertFalse(CommissionConfiguration.get_preservice_payment_enabled(tenant_id=self.tenant.id))
        self.assertFalse(CommissionConfiguration.get_escrow_production_enabled(tenant_id=self.tenant.id))
        self.assertFalse(CommissionConfiguration.get_objection_automation_enabled(tenant_id=self.tenant.id))
        self.assertFalse(CommissionConfiguration.get_dispute_release_enabled(tenant_id=self.tenant.id))

    def test_legacy_tenant_gets_no_preservice_invoice_or_intent(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        # PaymentDeadline is still recorded (PR-A's own data foundation),
        # but no pre-service PaymentIntent is created for a legacy tenant.
        self.assertTrue(PaymentDeadline.objects.filter(order=order, status=PaymentDeadlineStatus.PENDING).exists())
        self.assertFalse(
            PaymentIntent.objects.filter(
                tenant_id=self.tenant.id,
                reference_type="Order",
                reference_id=order.id,
            ).exists(),
        )

    def test_legacy_tenant_execution_starts_without_any_payment_guard(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        assignment = AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        session = ExecutionService.create_session(supplier_assignment=assignment)
        # No payment, no Escrow — must succeed exactly as before PR-B.
        started = ExecutionService.start_session(session_id=session.id)
        self.assertIsNotNone(started.started_at)

    def test_legacy_tenant_gets_no_objection_period_on_close(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        assignment = AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)

        session = ExecutionService.create_session(supplier_assignment=assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        ExecutionService.close_session(session_id=session.id, changed_by=self.actor)

        self.assertFalse(ObjectionPeriod.objects.filter(tenant_id=self.tenant.id, order=order).exists())
        self.assertFalse(EscrowRecord.objects.filter(tenant_id=self.tenant.id, order=order).exists())

    def test_enabling_preservice_payment_alone_does_not_enable_escrow_production(self):
        """A tenant may turn on pre-service payment collection without yet
        trusting the real Escrow production path — the two gates are
        independent (Section 18: 'independently configurable')."""
        self._enable_preservice_payment()
        self.assertTrue(CommissionConfiguration.get_preservice_payment_enabled(tenant_id=self.tenant.id))
        self.assertFalse(CommissionConfiguration.get_escrow_production_enabled(tenant_id=self.tenant.id))
