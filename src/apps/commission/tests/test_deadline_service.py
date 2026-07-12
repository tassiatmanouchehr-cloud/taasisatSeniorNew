from django.utils import timezone

from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
from apps.commission.services.deadline_service import PaymentDeadlineService
from apps.commission.services.errors import DeadlineError
from apps.jobs.models import JobDefinition
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor
from apps.orders.models import OrderStatus

from .helpers import CommissionTestCase


class PaymentDeadlineServiceTest(CommissionTestCase):
    def test_create_for_order_schedules_a_due_job_at_the_configured_default(self):
        order = self._make_order()
        before = timezone.now()
        deadline = PaymentDeadlineService.create_for_order(order=order)
        after = timezone.now()

        self.assertEqual(deadline.status, PaymentDeadlineStatus.PENDING)
        self.assertTrue(
            before + timezone.timedelta(minutes=30)
            <= deadline.deadline_at
            <= after + timezone.timedelta(minutes=30, seconds=5)
        )

        job = JobDefinition.objects.get(id=deadline.expiry_job_id)
        self.assertEqual(job.job_type, "commission.payment_deadline.expire")
        self.assertEqual(job.payload["payment_deadline_id"], str(deadline.id))
        self.assertEqual(job.scheduled_for, deadline.deadline_at)

    def test_extend_requires_permission(self):
        order = self._make_order()
        deadline = PaymentDeadlineService.create_for_order(order=order)
        unauthorized = make_actor(self.tenant, full_name="No Permission")

        with self.assertRaises(PermissionDenied):
            PaymentDeadlineService.extend(
                deadline_id=deadline.id,
                new_deadline_at=deadline.deadline_at + timezone.timedelta(minutes=15),
                reason="customer requested",
                actor=unauthorized,
            )

    def test_extend_requires_a_reason(self):
        order = self._make_order()
        deadline = PaymentDeadlineService.create_for_order(order=order)
        actor = make_actor(self.tenant, full_name="Platform Accounting")
        grant_permissions(self.tenant, actor, ["commission.deadline.extend"])

        with self.assertRaises(DeadlineError):
            PaymentDeadlineService.extend(
                deadline_id=deadline.id,
                new_deadline_at=deadline.deadline_at + timezone.timedelta(minutes=15),
                reason="",
                actor=actor,
            )

    def test_extend_records_full_audit_trail_and_reschedules_job(self):
        order = self._make_order()
        deadline = PaymentDeadlineService.create_for_order(order=order)
        actor = make_actor(self.tenant, full_name="Platform Accounting")
        grant_permissions(self.tenant, actor, ["commission.deadline.extend"])
        old_deadline_at = deadline.deadline_at
        new_deadline_at = old_deadline_at + timezone.timedelta(minutes=20)

        extended = PaymentDeadlineService.extend(
            deadline_id=deadline.id,
            new_deadline_at=new_deadline_at,
            reason="customer requested more time",
            actor=actor,
        )

        self.assertEqual(extended.deadline_at, new_deadline_at)
        extension = extended.extensions.get()
        self.assertEqual(extension.old_deadline_at, old_deadline_at)
        self.assertEqual(extension.new_deadline_at, new_deadline_at)
        self.assertEqual(extension.reason, "customer requested more time")
        self.assertEqual(extension.actor_id, actor.id)

        job = JobDefinition.objects.get(id=deadline.expiry_job_id)
        self.assertEqual(job.scheduled_for, new_deadline_at)
        self.assertEqual(job.next_run_at, new_deadline_at)

    def test_expire_due_cascades_order_reopen_and_assignment_expiry(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, actor, ["booking.assignment.assign"])

        from apps.booking.services.assignment_service import AssignmentService

        assignment = AssignmentService.assign(order_id=order.id, supplier=supplier, assigned_by=actor)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)
        self.assertEqual(order.assigned_supplier_id, supplier.id)

        deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        deadline.deadline_at = timezone.now() - timezone.timedelta(seconds=1)
        deadline.save(update_fields=["deadline_at"])

        PaymentDeadlineService.expire_due(deadline_id=deadline.id)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.NEW)
        self.assertIsNone(order.assigned_supplier_id)

        deadline.refresh_from_db()
        self.assertEqual(deadline.status, PaymentDeadlineStatus.EXPIRED)

        from apps.booking.models import SupplierAssignmentStatus

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, SupplierAssignmentStatus.EXPIRED)

    def test_expire_due_is_idempotent(self):
        order = self._make_order()
        deadline = PaymentDeadlineService.create_for_order(order=order)
        deadline.deadline_at = timezone.now() - timezone.timedelta(seconds=1)
        deadline.save(update_fields=["deadline_at"])

        first = PaymentDeadlineService.expire_due(deadline_id=deadline.id)
        second = PaymentDeadlineService.expire_due(deadline_id=deadline.id)

        self.assertEqual(first.status, PaymentDeadlineStatus.EXPIRED)
        self.assertEqual(second.status, PaymentDeadlineStatus.EXPIRED)
        self.assertEqual(first.resolved_at, second.resolved_at)

    def test_expire_due_not_yet_due_is_a_no_op(self):
        order = self._make_order()
        deadline = PaymentDeadlineService.create_for_order(order=order)

        result = PaymentDeadlineService.expire_due(deadline_id=deadline.id)

        self.assertEqual(result.status, PaymentDeadlineStatus.PENDING)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.NEW)

    def test_reassignment_after_expiry_opens_a_fresh_deadline_all_offers_expire(self):
        """Business Model Section 2: 'All previous offers expire... Order
        becomes available for new offers.'"""
        order = self._make_order()
        supplier_one = self._make_independent_supplier()
        actor = make_actor(self.tenant, full_name="Assigner")
        grant_permissions(self.tenant, actor, ["booking.assignment.assign"])

        from apps.booking.services.assignment_service import AssignmentService

        AssignmentService.assign(order_id=order.id, supplier=supplier_one, assigned_by=actor)
        first_deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        first_deadline.deadline_at = timezone.now() - timezone.timedelta(seconds=1)
        first_deadline.save(update_fields=["deadline_at"])
        PaymentDeadlineService.expire_due(deadline_id=first_deadline.id)

        first_deadline.refresh_from_db()
        self.assertEqual(first_deadline.status, PaymentDeadlineStatus.EXPIRED)

        supplier_two = self._make_independent_supplier()
        from apps.commission.services.snapshot_service import CommissionSnapshotService

        AssignmentService.assign(order_id=order.id, supplier=supplier_two, assigned_by=actor)

        order.refresh_from_db()
        self.assertEqual(order.assigned_supplier_id, supplier_two.id)

        second_deadline = PaymentDeadline.objects.get(order=order, status=PaymentDeadlineStatus.PENDING)
        self.assertNotEqual(second_deadline.id, first_deadline.id)

        second_snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier_two)
        self.assertEqual(second_snapshot.supplier_id, supplier_two.id)
        first_snapshot = order.commission_snapshots.get(supplier=supplier_one)
        self.assertNotEqual(second_snapshot.id, first_snapshot.id)
