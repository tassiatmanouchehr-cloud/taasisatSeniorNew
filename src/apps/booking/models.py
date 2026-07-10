"""
Booking / Assignment Lifecycle models — Module 03 foundation (Sprint 5A).

SupplierAssignment: a structured, versioned history record of one Level-1
(commercial) assignment attempt against an Order. It is NOT the source of
truth for the current assignment — Order.assigned_supplier remains that
(owned exclusively by apps.orders.services.status_machine). This model adds
richer, assignment-specific lifecycle/audit on top, populated as a side
effect of apps.booking.services.assignment_service.AssignmentService.

See docs/adr/ADR-002_MATCHING_ENGINE.md and the approved Module 03 proposal
for the surrounding architecture.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager


class SupplierAssignmentStatus(models.TextChoices):
    """
    Per the approved Module 03 refinement — ACTIVE is intentionally not a
    status here; CONFIRMED covers the "this is the operative assignment"
    meaning once a real commitment step exists.

    DECLINED (Epic 02 — Marketplace Operational Experience): the real
    commitment step CONFIRMED was reserved for. A provider explicitly
    confirms (-> CONFIRMED) or declines (-> DECLINED) an assignment via
    apps.booking.services.provider_actions.ProviderAssignmentActionService.
    Additive: existing rows are unaffected, this only adds a new reachable
    value.
    """

    PROPOSED = "proposed", "Proposed"
    ASSIGNED = "assigned", "Assigned"
    CONFIRMED = "confirmed", "Confirmed"
    DECLINED = "declined", "Declined"
    REPLACED = "replaced", "Replaced"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class AssignmentSource(models.TextChoices):
    """Where an assignment attempt originated."""

    MATCHING = "matching", "Matching"
    MANUAL = "manual", "Manual"
    API = "api", "API"
    IMPORT = "import", "Import"


class SupplierAssignment(models.Model):
    """One assignment attempt (create/replace/cancel) against an Order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="supplier_assignments",
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="supplier_assignments",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier", on_delete=models.CASCADE, related_name="assignments",
    )
    match_candidate = models.ForeignKey(
        "matching.MatchCandidate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="supplier_assignments",
    )

    status = models.CharField(
        max_length=20, choices=SupplierAssignmentStatus.choices,
        default=SupplierAssignmentStatus.PROPOSED, db_index=True,
    )
    assignment_source = models.CharField(max_length=20, choices=AssignmentSource.choices)
    assignment_sequence = models.IntegerField(
        help_text="1-indexed ordinal of this assignment attempt within its Order.",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text="Structured context for this assignment attempt (replaces free-text reason).",
    )
    superseded_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="supersedes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "booking_supplier_assignment"
        ordering = ["-assignment_sequence"]
        unique_together = [("order", "assignment_sequence")]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_suppassign_tenant_ord_st"),
        ]

    def __str__(self):
        return f"SupplierAssignment(order={self.order_id}, seq={self.assignment_sequence}) [{self.status}]"
