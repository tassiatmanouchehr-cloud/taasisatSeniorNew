"""
AvailabilityMutationService — Module 10 foundation.

The only code that creates/updates/removes ProviderWorkingWindow and
AvailabilityBlockedPeriod rows. Tenant is always derived from the supplier
passed in — callers never pass a separate tenant_id.
"""

from django.db import transaction
from django.utils import timezone

from ..models import AvailabilityBlockedPeriod, BlockedPeriodReason, ProviderWorkingWindow
from .errors import AvailabilityError


class AvailabilityMutationService:
    """Creates, updates, and removes working windows and blocked periods."""

    @classmethod
    @transaction.atomic
    def add_working_window(cls, *, supplier, day_of_week, start_time, end_time, metadata=None) -> ProviderWorkingWindow:
        cls._validate_time_range(start_time, end_time)

        return ProviderWorkingWindow.objects.create(
            tenant_id=supplier.tenant_id,
            supplier=supplier,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            metadata=metadata or {},
        )

    @classmethod
    @transaction.atomic
    def update_working_window(cls, *, window_id, start_time=None, end_time=None, is_active=None) -> ProviderWorkingWindow:
        window = ProviderWorkingWindow.objects.select_for_update().get(id=window_id)

        new_start = start_time if start_time is not None else window.start_time
        new_end = end_time if end_time is not None else window.end_time
        cls._validate_time_range(new_start, new_end)

        window.start_time = new_start
        window.end_time = new_end
        if is_active is not None:
            window.is_active = is_active
        window.save(update_fields=["start_time", "end_time", "is_active", "updated_at"])
        return window

    @classmethod
    def remove_working_window(cls, *, window_id) -> None:
        ProviderWorkingWindow.objects.filter(id=window_id).delete()

    @classmethod
    @transaction.atomic
    def add_blocked_period(
        cls, *, supplier, start_at, end_at, reason=BlockedPeriodReason.OTHER, notes="", metadata=None,
    ) -> AvailabilityBlockedPeriod:
        cls._validate_datetime_range(start_at, end_at)

        return AvailabilityBlockedPeriod.objects.create(
            tenant_id=supplier.tenant_id,
            supplier=supplier,
            start_at=start_at,
            end_at=end_at,
            reason=reason,
            notes=notes,
            metadata=metadata or {},
        )

    @classmethod
    def remove_blocked_period(cls, *, blocked_period_id) -> None:
        AvailabilityBlockedPeriod.objects.filter(id=blocked_period_id).delete()

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _validate_time_range(start_time, end_time) -> None:
        if start_time >= end_time:
            raise AvailabilityError("start_time must be strictly before end_time.")

    @staticmethod
    def _validate_datetime_range(start_at, end_at) -> None:
        if timezone.is_naive(start_at) or timezone.is_naive(end_at):
            raise AvailabilityError("start_at and end_at must be timezone-aware datetimes.")
        if start_at >= end_at:
            raise AvailabilityError("start_at must be strictly before end_at.")
