"""
Execution Service — Module 04 foundation (Sprint 6A).

Thin orchestration layer in front of apps.orders.services.status_machine —
the ONLY code that may mutate Order.status. This service adds a richer,
parallel execution lifecycle (ExecutionSession) as a side effect. It never
touches Order fields directly.

See the approved Module 04 architecture proposal for the surrounding
design. Per Sprint 6A scope:
- EN_ROUTE / ARRIVED presence tracking: deferred to Sprint 6B.
- execution_provider (Level-2 assignment): deferred — ExecutionSession
  references SupplierAssignment (Level-1) only.
- Customer confirmation workflow: no channel exists yet: complete_session()
  reaches PROVIDER_COMPLETED; close_session() is a distinct, separate call
  that finalizes the session AND the Order, not an automatic follow-on.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.booking.models import SupplierAssignmentStatus
from apps.kernel.events.base import ORDER_COMPLETED, ORDER_STARTED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.services.event_publisher import EventPublisher
from apps.kernel.services.permission_service import PermissionService
from apps.orders.services.status_machine import complete_order, start_order

from ..models import ExecutionSession, ExecutionSessionStatus, ExecutionSource
from ..permission_keys import EXECUTION_SESSION_CLOSE

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M04"

_CLOSABLE_STATUSES = (ExecutionSessionStatus.PROVIDER_COMPLETED, ExecutionSessionStatus.CUSTOMER_PENDING)


class ExecutionError(Exception):
    pass


class ExecutionService:
    """Orchestrates execution sessions while orders.status_machine remains the sole mutator of Order."""

    @classmethod
    @transaction.atomic
    def create_session(
        cls,
        *,
        supplier_assignment,
        execution_source=ExecutionSource.BOOKING,
        triggered_by=None,
        context_snapshot=None,
    ) -> ExecutionSession:
        order = supplier_assignment.order

        if supplier_assignment.status not in (
            SupplierAssignmentStatus.ASSIGNED,
            SupplierAssignmentStatus.CONFIRMED,
        ):
            raise ExecutionError(
                "SupplierAssignment must be assigned or confirmed before execution can begin.",
            )

        sequence = cls._next_sequence(order)

        session = ExecutionSession.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            supplier_assignment=supplier_assignment,
            status=ExecutionSessionStatus.SCHEDULED,
            execution_source=execution_source,
            execution_sequence=sequence,
            triggered_by=triggered_by,
            context_snapshot=context_snapshot or {},
        )

        EventPublisher.publish(
            tenant_id=order.tenant_id,
            event_type="Execution.Session.Created.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=session.id,
            source_entity_type="ExecutionSession",
            payload={
                "order_id": str(order.id),
                "supplier_assignment_id": str(supplier_assignment.id),
                "execution_source": execution_source,
                "execution_sequence": sequence,
            },
            actor_id=cls._actor_id(triggered_by),
        )

        return session

    @classmethod
    @transaction.atomic
    def start_session(cls, *, session_id, changed_by=None) -> ExecutionSession:
        session = ExecutionSession.objects.select_for_update().get(id=session_id)

        if session.status != ExecutionSessionStatus.SCHEDULED:
            raise ExecutionError(
                f"Cannot start an execution session in '{session.status}' status.",
            )

        # Financial Core PR-B (Section 20): a no-op for every tenant that
        # has not adopted pre-service payment — see
        # ExecutionPaymentGuardService's own docstring. Raises before any
        # mutation below if the gate is enabled and payment is not held.
        from apps.commission.services.errors import ExecutionPaymentGuardError
        from apps.commission.services.execution_payment_guard import ExecutionPaymentGuardService

        try:
            ExecutionPaymentGuardService.assert_can_start_execution(order=session.order)
        except ExecutionPaymentGuardError as exc:
            raise ExecutionError(str(exc)) from exc

        # The ONLY mutation of Order.status for this transition.
        start_order(order_id=session.order_id, changed_by=changed_by)

        session.status = ExecutionSessionStatus.IN_PROGRESS
        session.started_at = timezone.now()
        session.save(update_fields=["status", "started_at", "updated_at"])

        EventPublisher.publish(
            tenant_id=session.tenant_id,
            event_type="Execution.Session.Started.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=session.id,
            source_entity_type="ExecutionSession",
            payload={
                "order_id": str(session.order_id),
                "execution_sequence": session.execution_sequence,
            },
            actor_id=cls._actor_id(changed_by),
        )

        domain_event = DomainEvent(
            event_type=ORDER_STARTED,
            tenant_id=session.tenant_id,
            aggregate_type="Order",
            aggregate_id=session.order_id,
            actor_id=cls._actor_id(changed_by),
            payload={
                "execution_session_id": str(session.id),
                "recipient_id": cls._customer_person_id(session),
            },
        )
        transaction.on_commit(lambda: publish_domain_event(domain_event))

        return session

    @classmethod
    @transaction.atomic
    def complete_session(cls, *, session_id, changed_by=None) -> ExecutionSession:
        """Provider declares work done. Does NOT close the session or the Order — see close_session()."""
        session = ExecutionSession.objects.select_for_update().get(id=session_id)

        if session.status != ExecutionSessionStatus.IN_PROGRESS:
            raise ExecutionError(
                f"Cannot complete an execution session in '{session.status}' status.",
            )

        session.status = ExecutionSessionStatus.PROVIDER_COMPLETED
        session.provider_completed_at = timezone.now()
        session.save(update_fields=["status", "provider_completed_at", "updated_at"])

        EventPublisher.publish(
            tenant_id=session.tenant_id,
            event_type="Execution.Session.Completed.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=session.id,
            source_entity_type="ExecutionSession",
            payload={
                "order_id": str(session.order_id),
                "execution_sequence": session.execution_sequence,
            },
            actor_id=cls._actor_id(changed_by),
        )

        return session

    @classmethod
    @transaction.atomic
    def close_session(cls, *, session_id, changed_by=None) -> ExecutionSession:
        """Finalizes the session AND the Order (Order.status -> completed)."""
        session = ExecutionSession.objects.select_for_update().get(id=session_id)

        PermissionService.require(changed_by, EXECUTION_SESSION_CLOSE, tenant_id=session.tenant_id)

        if session.status not in _CLOSABLE_STATUSES:
            raise ExecutionError(
                f"Cannot close an execution session in '{session.status}' status.",
            )

        # The ONLY mutation of Order.status for this transition.
        complete_order(order_id=session.order_id, changed_by=changed_by)

        session.status = ExecutionSessionStatus.CLOSED
        session.closed_at = timezone.now()
        session.save(update_fields=["status", "closed_at", "updated_at"])

        # Financial Core PR-B (Section 7): a no-op for every tenant that has
        # not adopted pre-service payment. When adopted, this starts the
        # ObjectionPeriod against the order's HELD Escrow; if completion
        # somehow occurred without one (should already be prevented by
        # ExecutionPaymentGuardService at start_session() — an inconsistency,
        # not the normal path), this fails safely: it reports the gap via a
        # FINANCIAL audit record rather than fabricating an ObjectionPeriod/
        # Escrow, and does not block the session/order from closing (that
        # mutation has already committed above).
        cls._start_objection_period_if_applicable(session=session, changed_by=changed_by)

        EventPublisher.publish(
            tenant_id=session.tenant_id,
            event_type="Execution.Session.Closed.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=session.id,
            source_entity_type="ExecutionSession",
            payload={
                "order_id": str(session.order_id),
                "execution_sequence": session.execution_sequence,
            },
            actor_id=cls._actor_id(changed_by),
        )

        domain_event = DomainEvent(
            event_type=ORDER_COMPLETED,
            tenant_id=session.tenant_id,
            aggregate_type="Order",
            aggregate_id=session.order_id,
            actor_id=cls._actor_id(changed_by),
            payload={
                "execution_session_id": str(session.id),
                "recipient_id": cls._customer_person_id(session),
            },
        )
        transaction.on_commit(lambda: publish_domain_event(domain_event))

        return session

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _start_objection_period_if_applicable(cls, *, session, changed_by):
        from apps.commission.services.configuration import CommissionConfiguration

        order = session.order
        if not CommissionConfiguration.get_preservice_payment_enabled(tenant_id=order.tenant_id):
            return

        from apps.finance.models import EscrowRecord, EscrowStatus

        escrow = (
            EscrowRecord.objects.filter(
                tenant_id=order.tenant_id,
                order=order,
                status__in=(EscrowStatus.HELD, EscrowStatus.PARTIALLY_RELEASED, EscrowStatus.PARTIALLY_REFUNDED),
            )
            .order_by("-created_at")
            .first()
        )
        if escrow is None:
            from apps.kernel.models.audit import AuditClassification
            from apps.kernel.services.audit_service import AuditService

            AuditService.log(
                tenant_id=order.tenant_id,
                action="commission.objection.start_skipped_no_escrow",
                resource_type="ExecutionSession",
                module_id=SOURCE_MODULE,
                resource_id=session.id,
                audit_class=AuditClassification.FINANCIAL,
                reason=(
                    "Execution session closed (order completed) with pre-service payment enabled for this "
                    "tenant, but no HELD Escrow exists for the order — the objection period was not started. "
                    "This is an inconsistency (ExecutionPaymentGuardService should have prevented the session "
                    "from starting without one); investigate."
                ),
                after={"order_id": str(order.id)},
            )
            return

        from apps.commission.services.objection_service import ObjectionPeriodService

        ObjectionPeriodService.start_for_completion(
            order=order,
            execution_session=session,
            escrow=escrow,
            actor=changed_by,
        )

    @staticmethod
    def _next_sequence(order) -> int:
        return ExecutionSession.objects.filter(order=order).count() + 1

    @staticmethod
    def _actor_id(user):
        return getattr(user, "person_id", None)

    @staticmethod
    def _customer_person_id(session):
        order = session.order
        if order.customer_profile_id:
            return str(order.customer_profile.person_id)
        return None
