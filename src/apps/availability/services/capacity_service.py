"""
CapacityService — Module 10 foundation.

Capacity here is defined as a concurrent-open-assignment count against
apps.booking.models.SupplierAssignment (ASSIGNED/CONFIRMED — the
non-terminal statuses), not a time-window overlap count: Order/
SupplierAssignment carry no explicit duration today, so a true
overlapping-time-range capacity check isn't possible yet. Absence of a
CapacityRule means uncapped — capacity enforcement is opt-in per supplier.

Works identically for an independent-provider supplier or an
organization-type supplier — ServiceSupplier already unifies both, so there
is no separate "organization capacity" model or code path.
"""

from apps.booking.models import SupplierAssignment, SupplierAssignmentStatus

from ..models import CapacityRule

_ACTIVE_ASSIGNMENT_STATUSES = (SupplierAssignmentStatus.ASSIGNED, SupplierAssignmentStatus.CONFIRMED)


class CapacityService:
    """Reads/writes CapacityRule and evaluates current supplier engagement load."""

    @classmethod
    def set_capacity_rule(cls, *, supplier, max_concurrent_assignments, is_active=True) -> CapacityRule:
        rule, _ = CapacityRule.objects.update_or_create(
            supplier=supplier,
            defaults={
                "tenant_id": supplier.tenant_id,
                "max_concurrent_assignments": max_concurrent_assignments,
                "is_active": is_active,
            },
        )
        return rule

    @classmethod
    def get_active_engagement_count(cls, *, supplier) -> int:
        return SupplierAssignment.objects.filter(
            supplier=supplier, status__in=_ACTIVE_ASSIGNMENT_STATUSES,
        ).count()

    @classmethod
    def is_capacity_exceeded(cls, *, supplier) -> bool:
        try:
            rule = CapacityRule.objects.get(supplier=supplier, is_active=True)
        except CapacityRule.DoesNotExist:
            return False

        return cls.get_active_engagement_count(supplier=supplier) >= rule.max_concurrent_assignments
