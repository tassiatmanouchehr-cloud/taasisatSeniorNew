"""
ProviderAssignmentActionService — Epic 02 (Marketplace Operational
Experience).

The provider-facing counterpart to apps.booking.services.assignment_service
.AssignmentService: lets the ACTUAL assigned supplier confirm or decline
their own SupplierAssignment. Ownership-checked (never a role/permission-key
check alone) via apps.accounts.services.provider_identity
.resolve_supplier_for_user — the same "resolve the caller's own identity,
never accept one from the request" shape apps.portal.permissions uses.
AssignmentService.assign()'s existing "booking.assignment.assign" role
check stays exactly as-is; this module never touches it.

Extensible by design (Epic 02 architecture constraint #7): each provider
action is its own named classmethod plus an explicit transition table
(ALLOWED_PROVIDER_TRANSITIONS, mirroring apps.payments.services.transitions
.ALLOWED_TRANSITIONS) rather than an ad-hoc status write. Adding a future
action (counter offer, delay request, escalation, replacement request)
means adding another classmethod + transition-table entry — it never means
touching an existing method's contract or this file's existing methods.

Never mutates Order.assigned_supplier/Order.status — that remains the
exclusive concern of apps.orders.services.status_machine, reached only via
AssignmentService. This module only ever writes SupplierAssignment.status.
"""

from django.db import transaction

from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.kernel.events.base import PROVIDER_ASSIGNMENT_ACCEPTED, PROVIDER_ASSIGNMENT_REJECTED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event

from ..models import SupplierAssignment, SupplierAssignmentStatus


class ProviderAssignmentActionError(Exception):
    pass


# Which current statuses each named provider action may transition *from*.
# One entry per action — this is the "transition rules" table the
# extensibility constraint asks for; a future action adds a key here.
ALLOWED_PROVIDER_TRANSITIONS = {
    "confirm": {SupplierAssignmentStatus.PROPOSED, SupplierAssignmentStatus.ASSIGNED},
    "decline": {SupplierAssignmentStatus.PROPOSED, SupplierAssignmentStatus.ASSIGNED},
}


def _actor_id(user):
    return getattr(user, "person_id", None)


class ProviderAssignmentActionService:
    """Provider-initiated actions on the caller's own SupplierAssignment rows."""

    @classmethod
    def _resolve_owned_assignment(cls, *, assignment_id, actor) -> SupplierAssignment:
        supplier = resolve_supplier_for_user(actor)
        try:
            return SupplierAssignment.objects.for_tenant(supplier.tenant_id).select_related("order").get(
                id=assignment_id, supplier=supplier,
            )
        except SupplierAssignment.DoesNotExist:
            raise ProviderAssignmentActionError("Assignment not found.")

    @classmethod
    def _apply_transition(cls, *, assignment: SupplierAssignment, action: str, to_status: str) -> None:
        if assignment.status not in ALLOWED_PROVIDER_TRANSITIONS[action]:
            raise ProviderAssignmentActionError(
                f"Cannot {action} an assignment in status {assignment.status!r}.",
            )
        assignment.status = to_status
        assignment.save(update_fields=["status", "updated_at"])

    @classmethod
    @transaction.atomic
    def confirm(cls, *, assignment_id, actor) -> SupplierAssignment:
        assignment = cls._resolve_owned_assignment(assignment_id=assignment_id, actor=actor)
        cls._apply_transition(assignment=assignment, action="confirm", to_status=SupplierAssignmentStatus.CONFIRMED)

        event = DomainEvent(
            event_type=PROVIDER_ASSIGNMENT_ACCEPTED,
            tenant_id=assignment.tenant_id,
            aggregate_type="SupplierAssignment",
            aggregate_id=assignment.id,
            actor_id=_actor_id(actor),
            payload={"order_id": str(assignment.order_id)},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return assignment

    @classmethod
    @transaction.atomic
    def decline(cls, *, assignment_id, actor, reason: str = "") -> SupplierAssignment:
        assignment = cls._resolve_owned_assignment(assignment_id=assignment_id, actor=actor)
        cls._apply_transition(assignment=assignment, action="decline", to_status=SupplierAssignmentStatus.DECLINED)
        if reason:
            assignment.metadata = {**assignment.metadata, "decline_reason": reason}
            assignment.save(update_fields=["metadata"])

        event = DomainEvent(
            event_type=PROVIDER_ASSIGNMENT_REJECTED,
            tenant_id=assignment.tenant_id,
            aggregate_type="SupplierAssignment",
            aggregate_id=assignment.id,
            actor_id=_actor_id(actor),
            payload={"order_id": str(assignment.order_id), "reason": reason},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return assignment
