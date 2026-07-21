"""
Service Execution models — Module 04 foundation (Sprint 6A).

ExecutionSession: the execution lifecycle for a single Order, layered on
top of Order.status the same way booking.SupplierAssignment is layered on
top of Order.assigned_supplier. Order.status remains the coarse, canonical
status — owned exclusively by apps.orders.services.status_machine.
ExecutionSession never mutates Order fields directly; see
apps.execution.services.session_service.ExecutionService.

Per Sprint 6A refinement: no COMPLETED status here (PROVIDER_COMPLETED is
deliberately distinct from Order's own COMPLETED status, to avoid
conflating "provider says done" with the platform's final business state).
EN_ROUTE / ARRIVED presence tracking is deferred to Sprint 6B.
execution_provider (Level-2 assignment) is deferred — ExecutionSession
references SupplierAssignment (Level-1) only.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager


class ExecutionSessionStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    IN_PROGRESS = "in_progress", "In Progress"
    PROVIDER_COMPLETED = "provider_completed", "Provider Completed"
    CUSTOMER_PENDING = "customer_pending", "Customer Pending"
    CLOSED = "closed", "Closed"
    PAUSED = "paused", "Paused"
    INTERRUPTED = "interrupted", "Interrupted"


class ExecutionSource(models.TextChoices):
    """Where an execution session originated."""

    BOOKING = "booking", "Booking"
    MANUAL = "manual", "Manual"
    SYSTEM = "system", "System"
    RECOVERY = "recovery", "Recovery"
    API = "api", "API"


class ExecutionSession(models.Model):
    """One execution attempt for an Order, layered on top of Order.status."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="execution_sessions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="execution_sessions",
    )
    supplier_assignment = models.ForeignKey(
        "booking.SupplierAssignment",
        on_delete=models.PROTECT,
        related_name="execution_sessions",
    )

    status = models.CharField(
        max_length=20,
        choices=ExecutionSessionStatus.choices,
        default=ExecutionSessionStatus.SCHEDULED,
        db_index=True,
    )
    execution_source = models.CharField(max_length=20, choices=ExecutionSource.choices)
    execution_sequence = models.IntegerField(
        help_text="1-indexed ordinal of this execution attempt within its Order.",
    )

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    context_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of execution configuration/context at session creation time.",
    )

    started_at = models.DateTimeField(null=True, blank=True)
    provider_completed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "execution_session"
        ordering = ["-execution_sequence"]
        unique_together = [("order", "execution_sequence")]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_execsession_tenant_ord_st"),
        ]

    def __str__(self):
        return f"ExecutionSession(order={self.order_id}, seq={self.execution_sequence}) [{self.status}]"
