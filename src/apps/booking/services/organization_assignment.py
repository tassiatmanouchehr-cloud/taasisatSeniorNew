"""
OrganizationAssignmentService — Epic 02 (Marketplace Operational
Experience). Lets an organization admin manually assign one of their own
staff to an order.

Ownership-checked at two levels: the caller already administers
`organization` (verified by
apps.accounts.services.organization_identity.resolve_admin_organization
before this is ever called — apps.organization_portal never accepts an
organization id from the request, it always resolves "my organization"),
and the chosen staff membership actually belongs to that same
organization (verified here, via
apps.accounts.services.organization_staff.OrganizationStaffService
.resolve_staff_supplier).

Extensible by design (Epic 02 architecture constraint #8): manual
assignment is one named classmethod; a future strategy (automatic, bulk,
shift-based assignment) is another classmethod beside it, not a rewrite
of this one. Delegates to the existing, unmodified
apps.booking.services.assignment_service.AssignmentService.assign() —
never duplicates assignment logic, never mutates Order.assigned_supplier
itself.
"""

from django.db import transaction

from apps.accounts.services.errors import AccountsError
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.kernel.events.base import ORGANIZATION_ASSIGNMENT_CHANGED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event

from ..models import AssignmentSource
from .assignment_service import AssignmentError, AssignmentService


class OrganizationAssignmentError(Exception):
    pass


def _actor_id(user):
    return getattr(user, "person_id", None)


class OrganizationAssignmentService:
    """Organization-initiated assignment strategies. Only "manual" is
    implemented this phase — see the module docstring for how a future
    strategy is added without touching this method."""

    @classmethod
    @transaction.atomic
    def assign_manual(cls, *, organization, order_id, membership_id, actor=None):
        try:
            supplier = OrganizationStaffService.resolve_staff_supplier(
                organization=organization, membership_id=membership_id,
            )
        except AccountsError as exc:
            raise OrganizationAssignmentError(str(exc))

        try:
            assignment = AssignmentService.assign(
                order_id=order_id, supplier=supplier, assignment_source=AssignmentSource.MANUAL,
            )
        except AssignmentError as exc:
            raise OrganizationAssignmentError(str(exc))

        event = DomainEvent(
            event_type=ORGANIZATION_ASSIGNMENT_CHANGED,
            tenant_id=assignment.tenant_id,
            aggregate_type="SupplierAssignment",
            aggregate_id=assignment.id,
            actor_id=_actor_id(actor),
            payload={"order_id": str(order_id), "organization_id": str(organization.id), "strategy": "manual"},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return assignment
