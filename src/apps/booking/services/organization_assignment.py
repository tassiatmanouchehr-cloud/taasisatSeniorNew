"""
OrganizationAssignmentService — Epic 02 (Marketplace Operational
Experience). Lets an organization admin manually assign one of their own
staff to an order.

Ownership-checked at two levels: the caller already administers
`organization` (verified by
apps.organization_portal.permissions.resolve_organization() before this
is ever called — apps.organization_portal never accepts an organization
id from the request, it always resolves "my organization"), and the
chosen staff membership actually belongs to that same organization
(verified here, via
apps.accounts.services.organization_staff.OrganizationStaffService
.resolve_staff_supplier).

Extensible by design (Epic 02 architecture constraint #8): manual
assignment is one named classmethod; a future strategy (automatic, bulk,
shift-based assignment) is another classmethod beside it, not a rewrite
of this one. Delegates to the existing, unmodified
apps.booking.services.assignment_service.AssignmentService.assign() —
never duplicates assignment logic, never mutates Order.assigned_supplier
itself.

Actor/RBAC (Enterprise Architecture Review follow-up, finding #5): `actor`
is passed to AssignmentService.assign() as `ownership_authorized_by`, not
`assigned_by`. This means the "booking.assignment.assign" RBAC check
genuinely runs against that literal key. A `scope` kwarg is also passed
through here so, if an actor ever did carry a real RoleAssignment for
that exact key, a scoped grant would be consulted and not only a
platform-wide one — but as of this Epic no call site grants
"booking.assignment.assign" to an organization-scoped RoleAssignment (the
key Epic 04 Sprint 2 seeds via apps.accounts.services.organization_rbac
.OrganizationRoleSyncService is the distinct, not-yet-enforced
"organization.assignment.assign" — see apps.accounts.permission_keys's
own module docstring for the full accounting of this gap and why it is a
tracked Epic 05 remediation item, not a defect introduced here). In
practice, today, every call reaches PermissionService.require()'s
`ownership_authorized_by` fallback instead of a real RoleAssignment match
— an explicit, correctly actor-attributed "ownership_authorized" audit
entry, never a denial (which would break every organization admin) and
never mislabeled as system context (which would misrepresent a real human
action). Either way, `actor` ends up as SupplierAssignment.assigned_by and
as the actor_id on every event AssignmentService.assign() publishes —
never null, never attributed to "system" for a real admin-initiated call.

Eligibility enforcement (Epic 04 — Enterprise Organization Isolation):
before delegating to AssignmentService.assign(), this method verifies the
order is actually claimable by `organization` — either an ACTIVE
OrderOrganizationEligibility row exists, or the order is already assigned
to this organization (the reassignment case). An order with no eligibility
grant and no existing assignment to this organization is rejected before
any staff/order mutation happens, and the denial is published as an
auditable domain event — this is the fix for the previously-documented
"Organization Assignment Center is tenant-wide, not organization-scoped"
gap (see GAP_ANALYSIS.md, now closed by this Epic).
"""

from django.db import transaction

from apps.accounts.services.errors import AccountsError
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.kernel.events.base import ORGANIZATION_ACCESS_DENIED, ORGANIZATION_ASSIGNMENT_CHANGED, DomainEvent
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
    def assign_manual(cls, *, organization, order_id, membership_id, actor=None):
        """Deliberately NOT wrapped in @transaction.atomic at this level: the
        eligibility check below is read-only until it either denies (and
        must publish a denial event that survives regardless of what
        happens next) or proceeds to AssignmentService.assign(), which is
        already self-atomic. Wrapping this whole method in one atomic block
        would put the denial event's transaction.on_commit() callback
        inside a savepoint that then rolls back when
        OrganizationAssignmentError propagates — silently discarding the
        audit trail for every denied attempt."""
        from apps.orders.models import Order
        from apps.orders.services.eligibility_service import OrderEligibilityService

        try:
            order = Order.objects.for_tenant(organization.tenant_id).get(id=order_id)
        except Order.DoesNotExist:
            raise OrganizationAssignmentError("Order not found.")

        already_owned = cls._already_assigned_to_organization(order=order, organization=organization)

        if not already_owned and not OrderEligibilityService.is_eligible(order=order, organization=organization):
            cls._publish_access_denied(order=order, organization=organization, actor=actor)
            raise OrganizationAssignmentError(
                "This organization is not eligible to claim this order.",
            )

        try:
            supplier = OrganizationStaffService.resolve_staff_supplier(
                organization=organization, membership_id=membership_id,
            )
        except AccountsError as exc:
            raise OrganizationAssignmentError(str(exc))

        try:
            assignment = AssignmentService.assign(
                order_id=order_id, supplier=supplier, assignment_source=AssignmentSource.MANUAL,
                ownership_authorized_by=actor,
                scope={"scope_type": "organization", "scope_id": str(organization.id)},
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

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _already_assigned_to_organization(*, order, organization) -> bool:
        """True if the order's currently-assigned supplier resolves to
        `organization` — directly (SupplierType.ORGANIZATION) or via an
        active staff affiliation (SupplierType.ORGANIZATION_PROVIDER, Epic
        04 Sprint 3). The reassignment case: an organization that already
        owns an order's assignment may act on it again without a separate
        eligibility grant."""
        if order.assigned_supplier_id is None:
            return False

        assigned_organization = order.assigned_organization
        if assigned_organization is not None and assigned_organization.id == organization.id:
            return True

        supplier_ids = OrganizationStaffService.list_active_caregiver_supplier_ids(organization)
        return order.assigned_supplier_id in supplier_ids

    @classmethod
    def _publish_access_denied(cls, *, order, organization, actor) -> None:
        event = DomainEvent(
            event_type=ORGANIZATION_ACCESS_DENIED,
            tenant_id=order.tenant_id,
            aggregate_type="Order",
            aggregate_id=order.id,
            actor_id=_actor_id(actor),
            payload={"organization_id": str(organization.id), "reason": "not_eligible"},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
