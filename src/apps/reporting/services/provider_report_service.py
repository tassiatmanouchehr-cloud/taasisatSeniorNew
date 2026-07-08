"""
ProviderReportService — Module 16 foundation.

Read-only per-supplier performance aggregation over Execution/Booking/
Reviews. Never mutates any of them.
"""

import uuid

from django.db.models import Count, Q

from apps.booking.models import SupplierAssignment, SupplierAssignmentStatus
from apps.execution.models import ExecutionSession, ExecutionSessionStatus
from apps.kernel.models.supplier import ServiceSupplier
from apps.reviews.models import ReputationSnapshot

from ..dto import ProviderPerformanceReport

_ACTIVE_ASSIGNMENT_STATUSES = (SupplierAssignmentStatus.ASSIGNED, SupplierAssignmentStatus.CONFIRMED)


class ProviderReportService:
    """Deterministic, tenant-scoped provider performance aggregation."""

    @classmethod
    def get_report_for_supplier(cls, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> ProviderPerformanceReport:
        supplier = ServiceSupplier.objects.filter(tenant_id=tenant_id).get(id=supplier_id)
        return cls._build_report(supplier)

    @classmethod
    def list_reports(cls, tenant_id: uuid.UUID) -> tuple[ProviderPerformanceReport, ...]:
        suppliers = ServiceSupplier.objects.filter(tenant_id=tenant_id).order_by("id")
        return tuple(cls._build_report(supplier) for supplier in suppliers)

    @classmethod
    def _build_report(cls, supplier: ServiceSupplier) -> ProviderPerformanceReport:
        tenant_id = supplier.tenant_id

        # Two independent aggregates (not combined in one query) — SupplierAssignment and
        # ExecutionSession are separate one-to-many relations; joining both at once would
        # fan out and inflate the assignment counts.
        assignment_counts = SupplierAssignment.objects.for_tenant(tenant_id).filter(supplier=supplier).aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status__in=_ACTIVE_ASSIGNMENT_STATUSES)),
        )
        completed_services = ExecutionSession.objects.for_tenant(tenant_id).filter(
            supplier_assignment__supplier=supplier, status=ExecutionSessionStatus.CLOSED,
        ).count()

        try:
            snapshot = ReputationSnapshot.objects.filter(tenant_id=tenant_id).get(supplier=supplier)
            reputation_average = snapshot.average_score
            reputation_review_count = snapshot.review_count
        except ReputationSnapshot.DoesNotExist:
            reputation_average = supplier.reputation_score
            reputation_review_count = 0

        return ProviderPerformanceReport(
            tenant_id=tenant_id,
            supplier_id=supplier.id,
            completed_services=completed_services,
            reputation_average=reputation_average,
            reputation_review_count=reputation_review_count,
            availability_status=supplier.availability_status,
            total_assignments=assignment_counts["total"] or 0,
            active_assignments=assignment_counts["active"] or 0,
        )
