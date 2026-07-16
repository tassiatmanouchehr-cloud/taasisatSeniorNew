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

from django.db.models import Count

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

    @classmethod
    def bulk_is_capacity_exceeded(cls, *, supplier_ids) -> dict:
        """The batched counterpart of is_capacity_exceeded() — same rule
        (no active CapacityRule means uncapped, never exceeded), computed
        in exactly 2 queries regardless of how many supplier_ids are
        passed, for callers (e.g. DiscoveryRankingService.rank()) that
        need this for many suppliers in one pass instead of one query per
        supplier. Single-supplier call sites (provider_portal/
        organization_portal's own capacity display) keep using
        is_capacity_exceeded() unchanged — this is an addition, not a
        replacement."""
        supplier_ids = list(supplier_ids)
        if not supplier_ids:
            return {}

        rules_by_supplier_id = dict(
            CapacityRule.objects.filter(
                supplier_id__in=supplier_ids, is_active=True,
            ).values_list("supplier_id", "max_concurrent_assignments"),
        )
        if not rules_by_supplier_id:
            return dict.fromkeys(supplier_ids, False)

        engagement_counts = dict(
            SupplierAssignment.objects.filter(
                supplier_id__in=rules_by_supplier_id, status__in=_ACTIVE_ASSIGNMENT_STATUSES,
            ).values("supplier_id").annotate(count=Count("id")).values_list("supplier_id", "count"),
        )

        return {
            supplier_id: engagement_counts.get(supplier_id, 0) >= rules_by_supplier_id[supplier_id]
            if supplier_id in rules_by_supplier_id
            else False
            for supplier_id in supplier_ids
        }
