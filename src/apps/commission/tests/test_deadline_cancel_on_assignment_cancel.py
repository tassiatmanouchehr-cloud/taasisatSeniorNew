"""Remediation 7 (System Architect Review of PR #44):
AssignmentService.cancel() must cancel the order's pending PaymentDeadline
so a queued commission.payment_deadline.expire job becomes harmless
instead of firing a false expiry cascade against an order the caller has
already, separately, explicitly cancelled."""

from django.utils import timezone

from apps.booking.services.assignment_service import AssignmentService
from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
from apps.commission.services.deadline_service import PaymentDeadlineService
from apps.kernel.models.audit import AuditLog
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor

from .helpers import CommissionTestCase


class AssignmentCancelDeadlineTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self._enable_deadline_activation()
        self.actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, self.actor, ["booking.assignment.assign"])

    def _assign(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=self.actor)
        deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        return order, deadline

    def test_cancel_before_deadline_cancels_the_pending_deadline(self):
        order, deadline = self._assign()

        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)

        deadline.refresh_from_db()
        self.assertEqual(deadline.status, PaymentDeadlineStatus.CANCELLED)
        self.assertIsNotNone(deadline.resolved_at)

    def test_stale_queued_job_after_cancel_is_a_harmless_no_op(self):
        order, deadline = self._assign()
        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)

        # Simulate the already-queued expiry job firing anyway.
        deadline.refresh_from_db()
        deadline.deadline_at = timezone.now() - timezone.timedelta(seconds=1)
        deadline.save(update_fields=["deadline_at"])
        result = PaymentDeadlineService.expire_due(deadline_id=deadline.id)

        self.assertEqual(result.status, PaymentDeadlineStatus.CANCELLED)
        order.refresh_from_db()
        self.assertIsNone(order.assigned_supplier_id)  # already cleared by cancel(), not re-mutated by expire

    def test_repeated_cancel_is_idempotent_no_duplicate_audit(self):
        order, deadline = self._assign()

        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)
        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)

        entries = AuditLog.objects.filter(
            tenant_id=self.tenant.id,
            action="commission.payment_deadline.cancel",
            resource_id=deadline.id,
        )
        self.assertEqual(entries.count(), 1)

    def test_cancel_after_deadline_already_completed_does_not_reopen_it(self):
        order, deadline = self._assign()
        PaymentDeadlineService.mark_completed(order_id=order.id)

        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)

        deadline.refresh_from_db()
        self.assertEqual(deadline.status, PaymentDeadlineStatus.COMPLETED)

    def test_cancel_after_deadline_already_expired_does_not_mutate_it(self):
        order, deadline = self._assign()
        deadline.deadline_at = timezone.now() - timezone.timedelta(seconds=1)
        deadline.save(update_fields=["deadline_at"])
        PaymentDeadlineService.expire_due(deadline_id=deadline.id)
        deadline.refresh_from_db()
        self.assertEqual(deadline.status, PaymentDeadlineStatus.EXPIRED)
        resolved_at_before = deadline.resolved_at

        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)

        deadline.refresh_from_db()
        self.assertEqual(deadline.status, PaymentDeadlineStatus.EXPIRED)
        self.assertEqual(deadline.resolved_at, resolved_at_before)

    def test_cancel_with_no_assignment_at_all_is_a_no_op(self):
        order = self._make_order()
        AssignmentService.cancel(order_id=order.id, changed_by=self.actor)
        self.assertFalse(PaymentDeadline.objects.filter(order=order).exists())
