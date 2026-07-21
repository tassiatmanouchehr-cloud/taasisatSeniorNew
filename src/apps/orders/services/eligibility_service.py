"""
OrderEligibilityService — Epic 04 (Enterprise Organization Isolation).

The sole writer of OrderOrganizationEligibility. No other caller may
construct, update, or delete a row of that model directly — every grant,
revoke, or reactivation goes through this service, so there is exactly one
place that ever needs to change if the eligibility policy ever changes.

Eligibility policy for this Epic (System Architect Decision 1, Sprint
Planning §6): explicit grant only. There is no automatic/implicit rule —
not "single organization in a tenant is automatically eligible," not any
other business-signal-derived default. This is not a simplification of a
richer policy; it reflects a verified fact about the current repository:
apps.orders.services.order_creation.create_public_order()/
create_operator_order() carry no organization-derivable field of any kind
(no organization FK, no category-to-organization mapping, no operator-to-
organization mapping). There was no legitimate signal to build a default
policy from, so none was built. A future Epic that introduces such a
signal (e.g. category-based routing) adds a new call site to grant() —
this service's contract does not need to change for that.

Every write validates tenant consistency explicitly (System Architect
Decision 2) — never guesses or silently normalizes a mismatched or missing
tenant.

Auditing: apps.kernel.events.publisher.publish() unconditionally writes an
AuditLog row for every DomainEvent it dispatches (action=
"domain_event.<event_type>") — no separate AuditService.log() call is made
here, mirroring apps.booking.services.organization_assignment
.OrganizationAssignmentService's identical choice not to double-audit.
"""

from django.db import transaction
from django.utils import timezone

from apps.accounts.models.profiles import ProfileStatus
from apps.kernel.events.base import ORDER_ELIGIBILITY_GRANTED, ORDER_ELIGIBILITY_REVOKED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event

from ..models import EligibilityStatus, Order, OrderOrganizationEligibility


class OrderEligibilityError(Exception):
    pass


def _actor_id(user):
    return getattr(user, "person_id", None)


class OrderEligibilityService:
    """Grant/revoke/reactivate/query organization eligibility for an Order."""

    @classmethod
    def _validate_tenant_consistency(cls, *, order: Order, organization) -> None:
        if organization.tenant_id is None:
            raise OrderEligibilityError("Organization has no tenant; cannot grant eligibility.")
        if order.tenant_id is None:
            raise OrderEligibilityError("Order has no tenant; cannot grant eligibility.")
        if organization.tenant_id != order.tenant_id:
            raise OrderEligibilityError("Organization tenant does not match order tenant.")

    @classmethod
    @transaction.atomic
    def grant(cls, *, order: Order, organization, granted_by=None, source="manual") -> OrderOrganizationEligibility:
        """Idempotent: granting an already-ACTIVE pair is a no-op returning the
        existing row; granting a previously-WITHDRAWN pair reactivates it in
        place. Database-safe under concurrent grants via the (order,
        organization) unique constraint."""
        cls._validate_tenant_consistency(order=order, organization=organization)

        eligibility, created = OrderOrganizationEligibility.objects.get_or_create(
            order=order,
            organization=organization,
            defaults={
                "tenant_id": order.tenant_id,
                "status": EligibilityStatus.ACTIVE,
                "source": source,
                "granted_by": granted_by,
            },
        )
        if not created and eligibility.status != EligibilityStatus.ACTIVE:
            return cls.reactivate(order=order, organization=organization, granted_by=granted_by)
        if created:
            cls._publish_granted(eligibility, actor=granted_by)
        return eligibility

    @classmethod
    @transaction.atomic
    def reactivate(cls, *, order: Order, organization, granted_by=None) -> OrderOrganizationEligibility:
        """Reactivates a WITHDRAWN row in place — never inserts a duplicate
        row, per the unique_together constraint. A no-op (idempotent) if
        already ACTIVE."""
        cls._validate_tenant_consistency(order=order, organization=organization)

        try:
            eligibility = OrderOrganizationEligibility.objects.select_for_update().get(
                order=order,
                organization=organization,
            )
        except OrderOrganizationEligibility.DoesNotExist:
            return cls.grant(order=order, organization=organization, granted_by=granted_by)

        if eligibility.status == EligibilityStatus.ACTIVE:
            return eligibility

        eligibility.status = EligibilityStatus.ACTIVE
        eligibility.granted_by = granted_by
        eligibility.revoked_by = None
        eligibility.revoked_at = None
        eligibility.save(update_fields=["status", "granted_by", "revoked_by", "revoked_at"])
        cls._publish_granted(eligibility, actor=granted_by)
        return eligibility

    @classmethod
    @transaction.atomic
    def revoke(cls, *, order: Order, organization, revoked_by=None) -> OrderOrganizationEligibility | None:
        """Idempotent: revoking an already-WITHDRAWN or nonexistent pair is a
        safe no-op (returns the row, or None if it never existed)."""
        try:
            eligibility = OrderOrganizationEligibility.objects.select_for_update().get(
                order=order,
                organization=organization,
            )
        except OrderOrganizationEligibility.DoesNotExist:
            return None

        if eligibility.status == EligibilityStatus.WITHDRAWN:
            return eligibility

        eligibility.status = EligibilityStatus.WITHDRAWN
        eligibility.revoked_by = revoked_by
        eligibility.revoked_at = timezone.now()
        eligibility.save(update_fields=["status", "revoked_by", "revoked_at"])

        event = DomainEvent(
            event_type=ORDER_ELIGIBILITY_REVOKED,
            tenant_id=eligibility.tenant_id,
            aggregate_type="Order",
            aggregate_id=eligibility.order_id,
            actor_id=_actor_id(revoked_by),
            payload={"organization_id": str(eligibility.organization_id)},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
        return eligibility

    @classmethod
    def is_eligible(cls, *, order: Order, organization) -> bool:
        return (
            OrderOrganizationEligibility.objects.for_tenant(order.tenant_id)
            .filter(
                order=order,
                organization=organization,
                status=EligibilityStatus.ACTIVE,
                organization__status=ProfileStatus.ACTIVE,
            )
            .exists()
        )

    @classmethod
    def list_active_for_order(cls, order: Order):
        return (
            OrderOrganizationEligibility.objects.for_tenant(order.tenant_id)
            .filter(
                order=order,
                status=EligibilityStatus.ACTIVE,
            )
            .select_related("organization")
        )

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _publish_granted(cls, eligibility: OrderOrganizationEligibility, *, actor) -> None:
        event = DomainEvent(
            event_type=ORDER_ELIGIBILITY_GRANTED,
            tenant_id=eligibility.tenant_id,
            aggregate_type="Order",
            aggregate_id=eligibility.order_id,
            actor_id=_actor_id(actor),
            payload={"organization_id": str(eligibility.organization_id), "source": eligibility.source},
        )
        transaction.on_commit(lambda: publish_domain_event(event))
