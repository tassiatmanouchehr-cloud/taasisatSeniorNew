"""
ProviderExecutionService — Epic 02 (Marketplace Operational Experience).

Ownership-gated wrapper around apps.execution.services.session_service
.ExecutionService: lets the ACTUAL assigned provider start/complete their
own ExecutionSession. start_session()/complete_session() have no
permission or ownership check today (only close_session(), a separate
privileged/admin action, does) — this module adds the missing ownership
check as pure composition, without changing ExecutionService's existing
methods, signatures, or tests in any way.

Ownership check mirrors apps.booking.services.provider_actions: resolve
the caller's own ServiceSupplier via
apps.accounts.services.provider_identity.resolve_supplier_for_user, then
verify session.supplier_assignment.supplier_id matches it.

Publishes ProviderVisitStarted/ProviderVisitCompleted (audit-only, no
notification handler registered — see apps.kernel.events.base) in
addition to the ORDER_STARTED event start_session() already publishes;
complete_session() publishes no DomainEvent today, so
ProviderVisitCompleted is the first audit trail for that transition.
"""

from django.db import transaction

from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.kernel.events.base import PROVIDER_VISIT_COMPLETED, PROVIDER_VISIT_STARTED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event

from .session_service import ExecutionService


class ProviderExecutionActionError(Exception):
    pass


def _actor_id(user):
    return getattr(user, "person_id", None)


class ProviderExecutionService:
    """Provider-initiated start/complete on the caller's own ExecutionSession rows."""

    @classmethod
    def _resolve_owned_session(cls, *, session_id, actor):
        from ..models import ExecutionSession

        supplier = resolve_supplier_for_user(actor)
        try:
            session = (
                ExecutionSession.objects.for_tenant(supplier.tenant_id)
                .select_related(
                    "supplier_assignment",
                )
                .get(id=session_id)
            )
        except ExecutionSession.DoesNotExist:
            raise ProviderExecutionActionError("Visit not found.")

        if session.supplier_assignment.supplier_id != supplier.id:
            raise ProviderExecutionActionError("Visit not found.")
        return session

    @classmethod
    @transaction.atomic
    def start_visit(cls, *, session_id, actor):
        session = cls._resolve_owned_session(session_id=session_id, actor=actor)
        session = ExecutionService.start_session(session_id=session.id, changed_by=actor)

        event = DomainEvent(
            event_type=PROVIDER_VISIT_STARTED,
            tenant_id=session.tenant_id,
            aggregate_type="ExecutionSession",
            aggregate_id=session.id,
            actor_id=_actor_id(actor),
            payload={"order_id": str(session.order_id)},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return session

    @classmethod
    @transaction.atomic
    def complete_visit(cls, *, session_id, actor):
        session = cls._resolve_owned_session(session_id=session_id, actor=actor)
        session = ExecutionService.complete_session(session_id=session.id, changed_by=actor)

        event = DomainEvent(
            event_type=PROVIDER_VISIT_COMPLETED,
            tenant_id=session.tenant_id,
            aggregate_type="ExecutionSession",
            aggregate_id=session.id,
            actor_id=_actor_id(actor),
            payload={"order_id": str(session.order_id)},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return session
