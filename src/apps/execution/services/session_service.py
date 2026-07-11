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
            SupplierAssignmentStatus.ASSIGNED, SupplierAssignmentStatus.CONFIRMED,
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
