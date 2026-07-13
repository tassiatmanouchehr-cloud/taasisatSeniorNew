"""
PaymentDeadlineService — Financial Core PR-A.

Creates/extends/expires PaymentDeadline rows and drives the expiry cascade
(Business Model Section 2): accepted assignment -> expired, order reopened,
new offers possible. Enforced by a real scheduled apps.jobs job
(commission.payment_deadline.expire), not a lazy page-view check — see
jobs.py.

Idempotent by construction: expire_due() is safe to run twice for the same
PaymentDeadline (only PENDING deadlines transition; a second call on an
already-EXPIRED/COMPLETED/CANCELLED row is a no-op), matching every other
job handler in this codebase (apps.payments.jobs._retry_settlement's own
idempotency contract).

Deadline activation safety gate (System Architect Review of PR #44,
Remediation 6): CommissionConfiguration.get_deadline_activation_enabled()
is DISABLED by default for every existing and legacy tenant. The
authoritative business rule is pay-before-service — payment succeeds
BEFORE service execution, with the order reopening on non-payment being a
correct, safe cascade in that model. This repository's CURRENT order
lifecycle is execution-first (assign -> execute -> invoice -> pay); until
a real pre-service PaymentIntent -> successful callback -> Escrow hold
exists (a later PR), letting a scheduled expiry job call
AssignmentService.expire() would incorrectly reopen an order whose
(post-paid) execution may already be legitimately underway or complete.
create_for_order() therefore still creates the PaymentDeadline row (the
data foundation — statements/reporting/future-PR use is still correct to
record) but only schedules the real apps.jobs expiry job when the gate is
enabled for the order's tenant. expire_due() independently re-checks the
same gate before mutating anything, so a stale already-scheduled job (e.g.
one enqueued while the gate was briefly enabled) can never reopen an order
through an since-disabled path.
"""

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from apps.jobs.services.job_service import JobService
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..jobs import PAYMENT_DEADLINE_EXPIRE
from ..models.deadline import PaymentDeadline, PaymentDeadlineExtension, PaymentDeadlineStatus
from ..permission_keys import COMMISSION_DEADLINE_EXTEND
from .configuration import CommissionConfiguration
from .errors import DeadlineError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class PaymentDeadlineService:
    @classmethod
    @transaction.atomic
    def create_for_order(cls, *, order, assignment=None, actor=None) -> PaymentDeadline:
        cls._cancel_open_deadlines(order=order)

        seconds = CommissionConfiguration.get_payment_deadline_seconds(tenant_id=order.tenant_id)
        deadline_at = timezone.now() + timezone.timedelta(seconds=seconds)

        deadline = PaymentDeadline.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            assignment=assignment,
            original_deadline_at=deadline_at,
            deadline_at=deadline_at,
        )

        activation_enabled = CommissionConfiguration.get_deadline_activation_enabled(tenant_id=order.tenant_id)
        if activation_enabled:
            job = JobService.enqueue(
                job_type=PAYMENT_DEADLINE_EXPIRE,
                idempotency_key=str(deadline.id),
                tenant_id=order.tenant_id,
                payload={"payment_deadline_id": str(deadline.id)},
                scheduled_for=deadline_at,
            )
            deadline.expiry_job_id = job.id
            deadline.save(update_fields=["expiry_job_id", "updated_at"])
        else:
            logger.info(
                "Payment deadline activation disabled for tenant %s — PaymentDeadline %s recorded "
                "without scheduling an expiry job (Remediation 6 safety gate).",
                order.tenant_id,
                deadline.id,
            )

        AuditService.log(
            tenant_id=order.tenant_id,
            action="commission.payment_deadline.create",
            resource_type="PaymentDeadline",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=deadline.id,
            audit_class=AuditClassification.FINANCIAL,
            after={
                "order_id": str(order.id),
                "deadline_at": str(deadline_at),
                "activation_enabled": activation_enabled,
            },
        )

        return deadline

    @classmethod
    @transaction.atomic
    def extend(cls, *, deadline_id: uuid.UUID, new_deadline_at, reason: str, actor=None) -> PaymentDeadline:
        if not reason or not reason.strip():
            raise DeadlineError("A reason is required to extend a payment deadline.")

        deadline = PaymentDeadline.objects.select_for_update().get(id=deadline_id)
        PermissionService.require(actor, COMMISSION_DEADLINE_EXTEND, tenant_id=deadline.tenant_id)

        if deadline.status != PaymentDeadlineStatus.PENDING:
            raise DeadlineError(f"Cannot extend a payment deadline in '{deadline.status}' status.")
        if new_deadline_at <= deadline.deadline_at:
            raise DeadlineError("new_deadline_at must be later than the current deadline.")

        old_deadline_at = deadline.deadline_at
        deadline.deadline_at = new_deadline_at
        deadline.save(update_fields=["deadline_at", "updated_at"])

        cls._reschedule_expiry_job(deadline=deadline, new_deadline_at=new_deadline_at)

        PaymentDeadlineExtension.objects.create(
            tenant_id=deadline.tenant_id,
            deadline=deadline,
            order_id=deadline.order_id,
            actor=actor,
            old_deadline_at=old_deadline_at,
            new_deadline_at=new_deadline_at,
            reason=reason,
        )

        AuditService.log(
            tenant_id=deadline.tenant_id,
            action="commission.payment_deadline.extend",
            resource_type="PaymentDeadline",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=deadline.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            before={"deadline_at": str(old_deadline_at)},
            after={"deadline_at": str(new_deadline_at)},
        )

        return deadline

    @classmethod
    @transaction.atomic
    def mark_completed(cls, *, order_id: uuid.UUID) -> None:
        """Called once payment genuinely succeeds for the order — cancels the
        pending expiry sweep so a since-completed order is never reopened."""
        deadline = (
            PaymentDeadline.objects.select_for_update()
            .filter(order_id=order_id, status=PaymentDeadlineStatus.PENDING)
            .first()
        )
        if deadline is None:
            return
        deadline.status = PaymentDeadlineStatus.COMPLETED
        deadline.resolved_at = timezone.now()
        deadline.save(update_fields=["status", "resolved_at", "updated_at"])

    @classmethod
    @transaction.atomic
    def expire_due(cls, *, deadline_id: uuid.UUID) -> PaymentDeadline | None:
        """The job handler body — see jobs.py. Idempotent: a no-op if the
        deadline already left PENDING (paid, already expired, or cancelled
        by a newer assignment cycle)."""
        from apps.booking.services.assignment_service import AssignmentService

        deadline = PaymentDeadline.objects.select_for_update().get(id=deadline_id)
        if deadline.status != PaymentDeadlineStatus.PENDING:
            return deadline
        if deadline.deadline_at > timezone.now():
            # Extended since the job was scheduled; the job will be re-run
            # at the rescheduled next_run_at (see _reschedule_expiry_job).
            return deadline

        # Remediation 6 safety gate: re-checked here independently of
        # create_for_order()'s own check, so a stale already-scheduled job
        # (e.g. enqueued while the gate was briefly enabled, or a
        # leftover from before an operator disabled it) can never mutate
        # Order/SupplierAssignment state through an since-disabled path.
        if not CommissionConfiguration.get_deadline_activation_enabled(tenant_id=deadline.tenant_id):
            logger.warning(
                "commission.payment_deadline.expire job fired for tenant %s while deadline activation "
                "is disabled — ignoring without mutating order state (deadline=%s).",
                deadline.tenant_id,
                deadline.id,
            )
            return deadline

        deadline.status = PaymentDeadlineStatus.EXPIRED
        deadline.resolved_at = timezone.now()
        deadline.save(update_fields=["status", "resolved_at", "updated_at"])

        # Cascade: expire the assignment, release Order.assigned_supplier,
        # return the order to the reopened state — the single existing
        # mutation point for Order (apps.orders.services.status_machine),
        # reached only via AssignmentService per that service's own
        # docstring ("the ONLY code that may mutate Order.assigned_supplier
        # / Order.status").
        AssignmentService.expire(order_id=deadline.order_id, changed_by=None, reason="payment_deadline_expired")

        AuditService.log(
            tenant_id=deadline.tenant_id,
            action="commission.payment_deadline.expire",
            resource_type="PaymentDeadline",
            module_id=SOURCE_MODULE,
            actor_id=None,
            resource_id=deadline.id,
            audit_class=AuditClassification.FINANCIAL,
            after={"order_id": str(deadline.order_id), "status": deadline.status},
        )

        return deadline

    @classmethod
    @transaction.atomic
    def cancel_for_order(cls, *, order_id: uuid.UUID, actor=None) -> None:
        """Remediation 7 (System Architect Review of PR #44): cancels any
        still-PENDING PaymentDeadline for this order. Called by
        AssignmentService.cancel() so a queued
        commission.payment_deadline.expire job becomes a harmless,
        already-idempotent no-op (expire_due()'s own status guard) rather
        than firing a false expiry cascade — including
        AssignmentService.expire() itself — against an order the caller has
        already, separately, explicitly cancelled. Safe to call repeatedly
        (matches every other CANCELLED-status idempotency in this module)
        and safe to call when no PaymentDeadline exists at all for the
        order (a no-op, zero audit records written)."""
        open_deadlines = list(
            PaymentDeadline.objects.select_for_update().filter(
                order_id=order_id,
                status=PaymentDeadlineStatus.PENDING,
            )
        )
        now = timezone.now()
        for deadline in open_deadlines:
            deadline.status = PaymentDeadlineStatus.CANCELLED
            deadline.resolved_at = now
            deadline.save(update_fields=["status", "resolved_at", "updated_at"])
            AuditService.log(
                tenant_id=deadline.tenant_id,
                action="commission.payment_deadline.cancel",
                resource_type="PaymentDeadline",
                module_id=SOURCE_MODULE,
                actor_id=getattr(actor, "person_id", None),
                resource_id=deadline.id,
                audit_class=AuditClassification.FINANCIAL,
                after={"order_id": str(order_id), "status": deadline.status},
            )

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _cancel_open_deadlines(cls, *, order):
        open_deadlines = PaymentDeadline.objects.select_for_update().filter(
            order=order,
            status=PaymentDeadlineStatus.PENDING,
        )
        now = timezone.now()
        for deadline in open_deadlines:
            deadline.status = PaymentDeadlineStatus.CANCELLED
            deadline.resolved_at = now
            deadline.save(update_fields=["status", "resolved_at", "updated_at"])

    @classmethod
    def _reschedule_expiry_job(cls, *, deadline, new_deadline_at):
        from apps.jobs.models import JobDefinition, JobStatus

        if not deadline.expiry_job_id:
            return
        JobDefinition.objects.filter(
            id=deadline.expiry_job_id,
            status=JobStatus.PENDING,
        ).update(scheduled_for=new_deadline_at, next_run_at=new_deadline_at, updated_at=timezone.now())
