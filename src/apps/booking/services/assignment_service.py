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
    ) -> SupplierAssignment:
        """
        requested_start/requested_end are optional and conservative by
        design: availability/capacity validation (Module 10) only runs when
        BOTH are explicitly supplied by the caller. Every existing call site
        that omits them keeps today's exact behavior — nothing new runs.
        """
        from apps.orders.models import Order

        order = Order.objects.get(id=order_id)
        cls._ensure_same_tenant(order=order, supplier=supplier)

        PermissionService.require(assigned_by, "booking.assignment.assign", tenant_id=order.tenant_id)

        if requested_start is not None and requested_end is not None:
            cls._validate_availability(supplier=supplier, requested_start=requested_start, requested_end=requested_end)

        # The ONLY mutation of Order.assigned_supplier / Order.status.
        assign_supplier(order_id=order.id, supplier=supplier, changed_by=assigned_by)

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
            assigned_by=assigned_by,
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
            actor_id=cls._actor_id(assigned_by),
        )

        domain_event = DomainEvent(
            event_type=ORDER_ASSIGNED,
            tenant_id=order.tenant_id,
            aggregate_type="Order",
            aggregate_id=order.id,
            actor_id=cls._actor_id(assigned_by),
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
    ) -> SupplierAssignment:
        from apps.orders.models import Order

        order = Order.objects.get(id=order_id)
        cls._ensure_same_tenant(order=order, supplier=new_supplier)

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
