"""
Provider Availability, Scheduling & Capacity — Module 10 foundation.

Every model here keys off apps.kernel.models.supplier.ServiceSupplier — the
platform's universal supply-side abstraction — never CaregiverProfile or
OrganizationProfile directly. An organization-affiliated supplier
(SupplierType.ORGANIZATION) uses the exact same models and services as an
independent provider; there is no separate "organization capacity" concept.
"""

import uuid

from django.db import models

from apps.common.managers import TenantScopedManager


class DayOfWeek(models.IntegerChoices):
    """Matches Python's date.weekday() convention: Monday=0 .. Sunday=6."""

    MONDAY = 0, "Monday"
    TUESDAY = 1, "Tuesday"
    WEDNESDAY = 2, "Wednesday"
    THURSDAY = 3, "Thursday"
    FRIDAY = 4, "Friday"
    SATURDAY = 5, "Saturday"
    SUNDAY = 6, "Sunday"


class ProviderWorkingWindow(models.Model):
    """One recurring weekly working-hours block for a supplier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="provider_working_windows",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier", on_delete=models.CASCADE, related_name="working_windows",
    )

    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "availability_working_window"
        ordering = ["day_of_week", "start_time"]
        indexes = [
            models.Index(fields=["tenant", "supplier", "day_of_week"], name="idx_workwin_tenant_sup_day"),
        ]

    def __str__(self):
        return f"WorkingWindow(supplier={self.supplier_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})"


class BlockedPeriodReason(models.TextChoices):
    LEAVE = "LEAVE", "Leave"
    SICK = "SICK", "Sick"
    HOLIDAY = "HOLIDAY", "Holiday"
    MANUAL_BLOCK = "MANUAL_BLOCK", "Manual Block"
    OTHER = "OTHER", "Other"


class AvailabilityBlockedPeriod(models.Model):
    """A one-off unavailable time range for a supplier. Always overrides working windows."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="availability_blocked_periods",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier", on_delete=models.CASCADE, related_name="blocked_periods",
    )

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    reason = models.CharField(max_length=20, choices=BlockedPeriodReason.choices, default=BlockedPeriodReason.OTHER)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "availability_blocked_period"
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["tenant", "supplier", "start_at", "end_at"], name="idx_blockperiod_sup_range"),
        ]

    def __str__(self):
        return f"BlockedPeriod(supplier={self.supplier_id}, {self.start_at}..{self.end_at}) [{self.reason}]"


class CapacityRule(models.Model):
    """
    Maximum concurrent open assignments a supplier (independent provider or
    organization) can hold. Absence of a rule means uncapped — capacity
    enforcement is opt-in per supplier, not a default limit.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="capacity_rules",
    )
    supplier = models.OneToOneField(
        "kernel.ServiceSupplier", on_delete=models.CASCADE, related_name="capacity_rule",
    )

    max_concurrent_assignments = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "availability_capacity_rule"

    def __str__(self):
        return f"CapacityRule(supplier={self.supplier_id}, max={self.max_concurrent_assignments})"
