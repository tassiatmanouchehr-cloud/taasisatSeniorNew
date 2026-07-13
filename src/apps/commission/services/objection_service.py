"""
ObjectionPeriodService — Financial Core PR-B.

Starts when the canonical Execution/Completion engine
(apps.execution.services.session_service.ExecutionService.close_session())
closes a session whose order has a HELD Escrow. The customer may
explicitly approve (approve_by_customer) or a scheduled job may
auto-approve once the configured deadline passes with no dispute
(auto_approve_if_due) — either path marks the undisputed remaining Escrow
amount releasable and immediately produces one ReleaseInstruction for it.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.finance.services import EscrowService
from apps.kernel.events.base import (
    OBJECTION_APPROVED_BY_CUSTOMER,
    OBJECTION_AUTO_APPROVED,
    OBJECTION_PERIOD_OPENED,
    DomainEvent,
)
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..jobs import OBJECTION_PERIOD_AUTO_APPROVE
from ..models.objection import (
    ApprovalSource,
    ObjectionPeriod,
    ObjectionPeriodExtension,
    ObjectionPeriodStatus,
)
from ..permission_keys import COMMISSION_OBJECTION_EXTEND
from .authorization import assert_actor_is_order_customer
from .configuration import CommissionConfiguration
from .errors import ObjectionPeriodError
from .release_instruction_service import ReleaseInstructionService

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class ObjectionPeriodService:
    @classmethod
    @transaction.atomic
    def start_for_completion(cls, *, order, execution_session, escrow, actor=None) -> ObjectionPeriod:
        """Idempotent per escrow — a repeated call for the same Escrow
        (e.g. a retried close_session()) returns the existing
        ObjectionPeriod rather than creating a second one."""
        existing = ObjectionPeriod.objects.filter(tenant_id=order.tenant_id, escrow=escrow).first()
        if existing is not None:
            return existing

        seconds = CommissionConfiguration.get_objection_period_seconds(tenant_id=order.tenant_id)
        now = timezone.now()
        deadline = now + timezone.timedelta(seconds=seconds)

        objection = ObjectionPeriod.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            execution_session=execution_session,
            escrow=escrow,
            status=ObjectionPeriodStatus.OPEN,
            completion_at=now,
            objection_deadline=deadline,
        )

        if CommissionConfiguration.get_objection_automation_enabled(tenant_id=order.tenant_id):
            from apps.jobs.services.job_service import JobService

            job = JobService.enqueue(
                job_type=OBJECTION_PERIOD_AUTO_APPROVE,
                idempotency_key=str(objection.id),
                tenant_id=order.tenant_id,
                payload={"objection_period_id": str(objection.id)},
                scheduled_for=deadline,
            )
            objection.auto_approve_job_id = job.id
            objection.save(update_fields=["auto_approve_job_id"])

        AuditService.log(
            tenant_id=order.tenant_id,
            action="commission.objection.start",
            resource_type="ObjectionPeriod",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=objection.id,
            audit_class=AuditClassification.FINANCIAL,
            after={"order_id": str(order.id), "objection_deadline": str(deadline)},
        )
        cls._publish_customer_event(
            event_type=OBJECTION_PERIOD_OPENED,
            order=order,
            actor=actor,
            payload={"objection_deadline": str(deadline)},
        )

        return objection

    @classmethod
    @transaction.atomic
    def approve_by_customer(cls, *, objection_period_id, actor) -> ObjectionPeriod:
        """Only the customer who owns the order may approve. Idempotent:
        a repeated approval for an already-approved/closed period is a
        safe no-op returning the current state, not a duplicate movement/
        instruction/event/audit."""
        objection = ObjectionPeriod.objects.select_for_update().get(id=objection_period_id)
        assert_actor_is_order_customer(actor, objection.order, error_cls=ObjectionPeriodError)

        if objection.status not in (ObjectionPeriodStatus.OPEN, ObjectionPeriodStatus.DISPUTED):
            return objection

        now = timezone.now()
        objection.status = ObjectionPeriodStatus.CUSTOMER_APPROVED
        objection.customer_approved_at = now
        objection.approval_source = ApprovalSource.CUSTOMER
        objection.save(update_fields=["status", "customer_approved_at", "approval_source", "updated_at"])

        cls._release_undisputed_amount(objection=objection, source="CUSTOMER_APPROVAL", actor=actor)

        AuditService.log(
            tenant_id=objection.tenant_id,
            action="commission.objection.customer_approve",
            resource_type="ObjectionPeriod",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=objection.id,
            audit_class=AuditClassification.FINANCIAL,
            after={"status": objection.status, "approved_at": str(now)},
        )
        cls._publish_customer_event(
            event_type=OBJECTION_APPROVED_BY_CUSTOMER,
            order=objection.order,
            actor=actor,
            payload={"approved_at": str(now)},
        )

        return objection

    @classmethod
    @transaction.atomic
    def auto_approve_if_due(cls, *, objection_period_id) -> ObjectionPeriod | None:
        """The job handler body. A safe no-op (idempotent, harmless) unless
        ALL of: automation is enabled for the tenant, the period is
        genuinely OPEN (no dispute — a DISPUTED period requires human
        resolution or explicit customer approval), the deadline is truly
        due, and the order is still in a state consistent with a
        completed, undisputed cycle."""
        objection = ObjectionPeriod.objects.select_for_update().get(id=objection_period_id)

        if not CommissionConfiguration.get_objection_automation_enabled(tenant_id=objection.tenant_id):
            return objection
        if objection.status != ObjectionPeriodStatus.OPEN:
            return objection
        if timezone.now() < objection.objection_deadline:
            return objection

        now = timezone.now()
        objection.status = ObjectionPeriodStatus.AUTO_APPROVED
        objection.auto_approved_at = now
        objection.approval_source = ApprovalSource.AUTO
        objection.save(update_fields=["status", "auto_approved_at", "approval_source", "updated_at"])

        cls._release_undisputed_amount(objection=objection, source="AUTO_APPROVAL", actor=None)

        AuditService.log(
            tenant_id=objection.tenant_id,
            action="commission.objection.auto_approve",
            resource_type="ObjectionPeriod",
            module_id=SOURCE_MODULE,
            actor_id=None,
            actor_type="system",
            resource_id=objection.id,
            audit_class=AuditClassification.FINANCIAL,
            after={"status": objection.status, "auto_approved_at": str(now)},
        )
        cls._publish_customer_event(
            event_type=OBJECTION_AUTO_APPROVED,
            order=objection.order,
            actor=None,
            payload={"auto_approved_at": str(now)},
        )

        return objection

    @classmethod
    @transaction.atomic
    def extend(cls, *, objection_period_id, new_deadline_at, reason: str, actor=None) -> ObjectionPeriod:
        if not reason or not reason.strip():
            raise ObjectionPeriodError("A reason is required to extend an objection period.")

        objection = ObjectionPeriod.objects.select_for_update().get(id=objection_period_id)
        PermissionService.require(actor, COMMISSION_OBJECTION_EXTEND, tenant_id=objection.tenant_id)

        if objection.status not in (ObjectionPeriodStatus.OPEN, ObjectionPeriodStatus.DISPUTED):
            raise ObjectionPeriodError(f"Cannot extend an objection period in '{objection.status}' status.")
        if new_deadline_at <= objection.objection_deadline:
            raise ObjectionPeriodError("new_deadline_at must be later than the current deadline.")

        old_deadline_at = objection.objection_deadline
        objection.objection_deadline = new_deadline_at
        objection.save(update_fields=["objection_deadline", "updated_at"])

        if objection.auto_approve_job_id:
            from apps.jobs.models import JobDefinition, JobStatus

            JobDefinition.objects.filter(id=objection.auto_approve_job_id, status=JobStatus.PENDING).update(
                scheduled_for=new_deadline_at,
                next_run_at=new_deadline_at,
                updated_at=timezone.now(),
            )

        ObjectionPeriodExtension.objects.create(
            tenant_id=objection.tenant_id,
            objection_period=objection,
            order_id=objection.order_id,
            actor=actor,
            old_deadline_at=old_deadline_at,
            new_deadline_at=new_deadline_at,
            reason=reason,
        )

        AuditService.log(
            tenant_id=objection.tenant_id,
            action="commission.objection.extend",
            resource_type="ObjectionPeriod",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=objection.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            before={"objection_deadline": str(old_deadline_at)},
            after={"objection_deadline": str(new_deadline_at)},
        )

        return objection

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _publish_customer_event(*, event_type, order, actor, payload) -> None:
        if not order.customer_profile_id:
            return
        domain_event = DomainEvent(
            event_type=event_type,
            tenant_id=order.tenant_id,
            aggregate_type="Order",
            aggregate_id=order.id,
            actor_id=getattr(actor, "person_id", None),
            payload={"recipient_id": str(order.customer_profile.person_id), **payload},
        )
        transaction.on_commit(lambda: publish_domain_event(domain_event))

    @classmethod
    def _release_undisputed_amount(cls, *, objection, source, actor):
        from apps.finance.models import EscrowRecord

        escrow = EscrowRecord.objects.select_for_update().get(id=objection.escrow_id)
        amount_irr = escrow.remaining_amount_irr
        if amount_irr <= 0:
            return None

        EscrowService.mark_releasable(
            escrow_id=escrow.id,
            amount_irr=amount_irr,
            source_type="ObjectionPeriod",
            source_id=objection.id,
            actor=actor,
            reason=f"Undisputed amount released via {source.lower()}.",
            idempotency_key=f"objection-releasable:{objection.id}",
        )

        return ReleaseInstructionService.create(
            escrow=escrow,
            order=objection.order,
            invoice=escrow.source_document,
            commission_snapshot=escrow.commission_snapshot,
            source=source,
            amount_irr=amount_irr,
            actor=actor,
            reason=f"Undisputed amount released via {source.lower()}.",
            idempotency_key=f"objection-release:{objection.id}",
        )
