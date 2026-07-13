"""Remediation 6 (System Architect Review of PR #44): the deadline
activation safety gate. The authoritative business rule is pay-before-
service with Escrow, but this repository's current order lifecycle is
execution-first — until a real pre-service PaymentIntent/Escrow flow
exists, a scheduled expiry job must never be allowed to reopen a real
order. Default is DISABLED for every tenant."""

from django.utils import timezone

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
from apps.commission.services.deadline_service import PaymentDeadlineService
from apps.jobs.models import JobDefinition
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.orders.models import OrderStatus

from .helpers import CommissionTestCase


class DeadlineActivationGateDisabledByDefaultTest(CommissionTestCase):
    """No self._enable_deadline_activation() call anywhere in this class —
    proving the real, un-overridden default is DISABLED."""

    def test_create_for_order_records_deadline_but_schedules_no_job(self):
        order = self._make_order()
        deadline = PaymentDeadlineService.create_for_order(order=order)

        self.assertEqual(deadline.status, PaymentDeadlineStatus.PENDING)
        self.assertIsNone(deadline.expiry_job_id)
        self.assertFalse(
            JobDefinition.objects.filter(
                job_type="commission.payment_deadline.expire", tenant_id=self.tenant.id
            ).exists()
        )

    def test_assign_does_not_schedule_a_deadline_expiry_job(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, actor, ["booking.assignment.assign"])

        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=actor)

        deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        self.assertIsNone(deadline.expiry_job_id)

    def test_expire_due_does_not_mutate_order_when_gate_disabled(self):
        """Even a deadline whose deadline_at has already passed must not be
        expired while the gate is disabled — expire_due() re-checks the
        gate independently of create_for_order()."""
        order = self._make_order()
        supplier = self._make_independent_supplier()
        actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, actor, ["booking.assignment.assign"])
        assignment = AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=actor)

        deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        deadline.deadline_at = timezone.now() - timezone.timedelta(seconds=1)
        deadline.save(update_fields=["deadline_at"])

        result = PaymentDeadlineService.expire_due(deadline_id=deadline.id)

        self.assertEqual(result.status, PaymentDeadlineStatus.PENDING)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)
        self.assertEqual(order.assigned_supplier_id, supplier.id)

        from apps.booking.models import SupplierAssignmentStatus

        assignment.refresh_from_db()
        self.assertNotEqual(assignment.status, SupplierAssignmentStatus.EXPIRED)


class DeadlineActivationGateEnabledTest(CommissionTestCase):
    """Once explicitly enabled for a tenant, the full existing PR-A
    deadline/expiry mechanism continues to work unchanged — see
    test_deadline_service.py for the comprehensive behavioral suite; this
    only proves the gate itself flips the behavior on."""

    def setUp(self):
        super().setUp()
        self._enable_deadline_activation()

    def test_create_for_order_schedules_a_job_when_enabled(self):
        order = self._make_order()
        deadline = PaymentDeadlineService.create_for_order(order=order)
        self.assertIsNotNone(deadline.expiry_job_id)
        self.assertTrue(JobDefinition.objects.filter(id=deadline.expiry_job_id).exists())

    def test_expire_due_reopens_order_when_enabled(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, actor, ["booking.assignment.assign"])
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=actor)

        deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        deadline.deadline_at = timezone.now() - timezone.timedelta(seconds=1)
        deadline.save(update_fields=["deadline_at"])

        result = PaymentDeadlineService.expire_due(deadline_id=deadline.id)

        self.assertEqual(result.status, PaymentDeadlineStatus.EXPIRED)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.NEW)
