"""
Assignment Service — Module 03 Booking foundation (Sprint 5A).

Thin orchestration layer in front of apps.orders.services.status_machine —
the ONLY code that may mutate Order.assigned_supplier / Order.status. This
service adds structured, versioned assignment history and wires
matching.MatchCandidate selection as side effects. It never touches Order
fields directly.

See docs/adr/ADR-002_MATCHING_ENGINE.md (Module 03 section) for the
approved architecture this implements.
"""

import logging

from django.db import transaction

from apps.kernel.events.base import ORDER_ASSIGNED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.services.event_publisher import EventPublisher
from apps.kernel.services.permission_service import PermissionService
from apps.matching.services.match_orchestrator import MatchOrchestrator
from apps.orders.services.status_machine import assign_supplier, remove_supplier, replace_supplier

from ..permission_keys import BOOKING_ASSIGNMENT_ASSIGN

from ..models import AssignmentSource, SupplierAssignment, SupplierAssignmentStatus
from .configuration import BookingConfiguration

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M03"


class AssignmentError(Exception):
    pass


class AssignmentService:
    """Orchestrates supplier assignment while orders.status_machine remains the sole mutator of Order."""

    @classmethod
    @transaction.atomic
    def assign(
        cls,
        *,
        order_id,
        supplier,
        match_candidate=None,
        assigned_by=None,
        assignment_source=None,
        metadata=None,
        requested_start=None,
        requested_end=None,
        ownership_authorized_by=None,
        scope=None,
    ) -> SupplierAssignment:
        """
        requested_start/requested_end are optional and conservative by
        design: availability/capacity validation (Module 10) only runs when
        BOTH are explicitly supplied by the caller. Every existing call site
        that omits them keeps today's exact behavior — nothing new runs.

        ownership_authorized_by: only consulted when assigned_by is None —
        see PermissionService.require()'s docstring for the full reasoning.
        A real, named actor authorized by a verified ownership check
        upstream (not an RBAC role, which may not exist for them yet).
        Becomes the effective actor for permission evaluation *and*
        attribution (SupplierAssignment.assigned_by, OrderStatusHistory
        .changed_by, the published events' actor_id) — never silently
        recorded as an anonymous/system action.

        scope: optional {"scope_type": ..., "scope_id": ...} passed through
        to PermissionService.require() (Epic 04 — Enterprise Organization
        Isolation). Lets an organization-scoped caller's real, synced
        scoped role grant be consulted instead of only a platform-wide one.
        Omitted (None) by every pre-Epic-04 call site — unchanged behavior
        for those.

        Concurrency (Epic 04): Order.objects.select_for_update() is the
        first statement, before the eligibility/permission checks and
        before assign_supplier() — serializes concurrent assignment
        attempts against the same order, database-safe rather than
        read-before-write. Mirrors the identical pattern used for
        PaymentIntent in apps.payments.services
        .settlement_orchestration_service (Epic 03 Sprint 1).
        """
        from apps.orders.models import Order

        order = Order.objects.select_for_update().get(id=order_id)
        cls._ensure_same_tenant(order=order, supplier=supplier)

        PermissionService.require(
            assigned_by, BOOKING_ASSIGNMENT_ASSIGN, tenant_id=order.tenant_id,
            ownership_authorized_by=ownership_authorized_by, scope=scope,
        )
        effective_actor = assigned_by or ownership_authorized_by

        if requested_start is not None and requested_end is not None:
            cls._validate_availability(supplier=supplier, requested_start=requested_start, requested_end=requested_end)

        # The ONLY mutation of Order.assigned_supplier / Order.status.
        assign_supplier(order_id=order.id, supplier=supplier, changed_by=effective_actor)

        resolved_source = cls._resolve_source(assignment_source, match_candidate)
        status = cls._initial_status(tenant_id=order.tenant_id)
        sequence = cls._next_sequence(order)

        assignment = SupplierAssignment.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            supplier=supplier,
            match_candidate=match_candidate,
            status=status,
            assignment_source=resolved_source,
            assignment_sequence=sequence,
            assigned_by=effective_actor,
            metadata=metadata or {},
        )

        cls._mark_candidate_selected(match_candidate)

        EventPublisher.publish(
            tenant_id=order.tenant_id,
            event_type="Booking.Assignment.Created.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=assignment.id,
            source_entity_type="SupplierAssignment",
            payload={
                "order_id": str(order.id),
                "supplier_id": str(supplier.id),
                "match_candidate_id": str(match_candidate.id) if match_candidate else None,
                "assignment_source": resolved_source,
                "status": status,
                "assignment_sequence": sequence,
            },
            actor_id=cls._actor_id(effective_actor),
        )

        domain_event = DomainEvent(
            event_type=ORDER_ASSIGNED,
            tenant_id=order.tenant_id,
            aggregate_type="Order",
            aggregate_id=order.id,
            actor_id=cls._actor_id(effective_actor),
            payload={
                "supplier_id": str(supplier.id),
                "assignment_id": str(assignment.id),
                "recipient_id": cls._customer_person_id(order),
            },
        )
        transaction.on_commit(lambda: publish_domain_event(domain_event))

        return assignment

    @classmethod
    @transaction.atomic
    def replace(
        cls,
        *,
        order_id,
        new_supplier,
        match_candidate=None,
        assigned_by=None,
        assignment_source=None,
        metadata=None,
        ownership_authorized_by=None,
        scope=None,
    ) -> SupplierAssignment:
        """Concurrency (Epic 04): Order.objects.select_for_update() is the
        first statement, mirroring assign()'s own locking — see that
        method's docstring for the full reasoning.

        Authorization (Epic 05 confirmed authorization defect fix): this
        method previously performed no PermissionService check at all —
        assign() has always required "booking.assignment.assign", replace()
        (a reassignment, the same underlying capability) required nothing.
        No production call site exists yet for replace() (confirmed by
        inspection — only test code calls it today), so this closes the
        gap before a real caller is ever wired up, rather than after.
        Reuses BOOKING_ASSIGNMENT_ASSIGN — reassignment is not a distinct
        product capability from assignment, so a second key would be
        speculative (see the canonical permission-key registry's own
        docstring, apps/kernel/permissions/keys.py)."""
        from apps.orders.models import Order

        order = Order.objects.select_for_update().get(id=order_id)
        cls._ensure_same_tenant(order=order, supplier=new_supplier)

        PermissionService.require(
            assigned_by, BOOKING_ASSIGNMENT_ASSIGN, tenant_id=order.tenant_id,
            ownership_authorized_by=ownership_authorized_by, scope=scope,
        )

        if not BookingConfiguration.get_reassignment_enabled(tenant_id=order.tenant_id):
            raise AssignmentError("Reassignment is disabled for this tenant.")

        previous = cls._current_assignment(order)

        # The ONLY mutation of Order.assigned_supplier / Order.status.
        replace_supplier(order_id=order.id, new_supplier=new_supplier, changed_by=assigned_by)

        resolved_source = cls._resolve_source(assignment_source, match_candidate)
        status = cls._initial_status(tenant_id=order.tenant_id)
        sequence = cls._next_sequence(order)

        new_assignment = SupplierAssignment.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            supplier=new_supplier,
            match_candidate=match_candidate,
            status=status,
            assignment_source=resolved_source,
            assignment_sequence=sequence,
            assigned_by=assigned_by,
            metadata=metadata or {},
        )

        if previous is not None:
            previous.status = SupplierAssignmentStatus.REPLACED
            previous.superseded_by = new_assignment
            previous.save(update_fields=["status", "superseded_by", "updated_at"])

        cls._mark_candidate_selected(match_candidate)

        EventPublisher.publish(
            tenant_id=order.tenant_id,
            event_type="Booking.Assignment.Replaced.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=new_assignment.id,
            source_entity_type="SupplierAssignment",
            payload={
                "order_id": str(order.id),
                "previous_supplier_id": str(previous.supplier_id) if previous else None,
                "new_supplier_id": str(new_supplier.id),
                "assignment_source": resolved_source,
                "assignment_sequence": sequence,
            },
            actor_id=cls._actor_id(assigned_by),
        )

        return new_assignment

    @classmethod
    @transaction.atomic
    def cancel(cls, *, order_id, changed_by=None, metadata=None) -> SupplierAssignment | None:
        from apps.orders.models import Order

        order = Order.objects.get(id=order_id)
        current = cls._current_assignment(order)

        # The ONLY mutation of Order.assigned_supplier / Order.status.
        remove_supplier(order_id=order.id, changed_by=changed_by)

        if current is not None:
            current.status = SupplierAssignmentStatus.CANCELLED
            if metadata:
                current.metadata = {**current.metadata, **metadata}
            current.save(update_fields=["status", "metadata", "updated_at"])

        EventPublisher.publish(
            tenant_id=order.tenant_id,
            event_type="Booking.Assignment.Cancelled.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=current.id if current else None,
            source_entity_type="SupplierAssignment",
            payload={
                "order_id": str(order.id),
                "supplier_id": str(current.supplier_id) if current else None,
            },
            actor_id=cls._actor_id(changed_by),
        )

        return current

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _ensure_same_tenant(*, order, supplier):
        if supplier.tenant_id != order.tenant_id:
            raise AssignmentError("Supplier tenant does not match order tenant.")

    @staticmethod
    def _validate_availability(*, supplier, requested_start, requested_end):
        """Only reached when the caller explicitly supplied both bounds — see assign()."""
        from apps.availability.services import AvailabilityConfiguration, AvailabilityQueryService, CapacityService

        if not AvailabilityConfiguration.get_enforcement_enabled(tenant_id=supplier.tenant_id):
            return

        if not AvailabilityQueryService.is_supplier_available(
            supplier=supplier, start=requested_start, end=requested_end,
        ):
            raise AssignmentError("Supplier is not available for the requested time range.")

        if CapacityService.is_capacity_exceeded(supplier=supplier):
            raise AssignmentError("Supplier capacity is exceeded.")

    @staticmethod
    def _resolve_source(assignment_source, match_candidate) -> str:
        if assignment_source:
            return assignment_source
        return AssignmentSource.MATCHING if match_candidate is not None else AssignmentSource.MANUAL

    @staticmethod
    def _initial_status(*, tenant_id) -> str:
        if BookingConfiguration.get_auto_accept_enabled(tenant_id=tenant_id):
            return SupplierAssignmentStatus.CONFIRMED
        return SupplierAssignmentStatus.ASSIGNED

    @staticmethod
    def _next_sequence(order) -> int:
        return SupplierAssignment.objects.filter(order=order).count() + 1

    @staticmethod
    def _current_assignment(order) -> SupplierAssignment | None:
        return (
            SupplierAssignment.objects.filter(order=order)
            .exclude(status__in=[SupplierAssignmentStatus.REPLACED, SupplierAssignmentStatus.CANCELLED])
            .order_by("-assignment_sequence")
            .first()
        )

    @staticmethod
    def _mark_candidate_selected(match_candidate):
        if match_candidate is not None:
            MatchOrchestrator.mark_candidate_selected(match_candidate_id=match_candidate.id)

    @staticmethod
    def _actor_id(user):
        return getattr(user, "person_id", None)

    @staticmethod
    def _customer_person_id(order):
        if order.customer_profile_id:
            return str(order.customer_profile.person_id)
        return None
