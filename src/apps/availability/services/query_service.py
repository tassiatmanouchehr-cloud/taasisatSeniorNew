"""
AvailabilityQueryService — Module 10 foundation.

Pure read-side evaluation: does a supplier's configured schedule (working
windows minus blocked periods) cover an explicit, caller-supplied
[start, end) range? Deliberately takes explicit datetimes rather than an
Order — Order's own scheduling fields (scheduled_for / requested_time_window)
are not a clean range today, so this service stays decoupled from that.

Absence of any configured working window is treated conservatively as
"not available" (fail-closed) — an unconfigured schedule is unknown, not open.

Foundation scope: a requested range must fall within a single local
calendar day. Ranges spanning local midnight (e.g. an overnight shift) are
rejected with AvailabilityError rather than silently evaluated — that is
deferred to a follow-up once there's a concrete overnight-shift use case
to design correctly against.
"""

from django.utils import timezone

from ..models import AvailabilityBlockedPeriod, ProviderWorkingWindow
from .errors import AvailabilityError


class AvailabilityQueryService:
    """Evaluates supplier availability for an explicit time range."""

    @classmethod
    def is_supplier_available(cls, *, supplier, start, end) -> bool:
        cls._validate_range(start, end)

        if cls._has_blocking_overlap(supplier=supplier, start=start, end=end):
            return False

        return cls._covered_by_working_window(supplier=supplier, start=start, end=end)

    @classmethod
    def get_working_windows(cls, *, supplier, day_of_week=None):
        qs = ProviderWorkingWindow.objects.filter(supplier=supplier, is_active=True)
        if day_of_week is not None:
            qs = qs.filter(day_of_week=day_of_week)
        return qs

    @classmethod
    def get_blocked_periods(cls, *, supplier, start=None, end=None):
        qs = AvailabilityBlockedPeriod.objects.filter(supplier=supplier)
        if start is not None and end is not None:
            qs = qs.filter(start_at__lt=end, end_at__gt=start)
        return qs

    @classmethod
    def get_working_window_for_supplier(cls, *, supplier, window_id):
        """Ownership-scoped single-row lookup — Epic 02 (Marketplace Operational
        Experience), so apps.provider_portal can verify a window belongs to the
        caller before mutating it, without filtering a queryset in the view."""
        return ProviderWorkingWindow.objects.filter(supplier=supplier, id=window_id).first()

    @classmethod
    def get_blocked_period_for_supplier(cls, *, supplier, blocked_period_id):
        """Ownership-scoped single-row lookup — Epic 02, same reasoning as
        get_working_window_for_supplier()."""
        return AvailabilityBlockedPeriod.objects.filter(supplier=supplier, id=blocked_period_id).first()

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _validate_range(start, end) -> None:
        if start is None or end is None:
            raise AvailabilityError("Both start and end are required.")
        if timezone.is_naive(start) or timezone.is_naive(end):
            raise AvailabilityError("start and end must be timezone-aware datetimes.")
        if start >= end:
            raise AvailabilityError("start must be strictly before end.")

        local_start = timezone.localtime(start)
        local_end = timezone.localtime(end)
        if local_start.date() != local_end.date():
            raise AvailabilityError(
                "Requested range spans local midnight; overnight ranges are not supported yet.",
            )

    @staticmethod
    def _has_blocking_overlap(*, supplier, start, end) -> bool:
        return AvailabilityBlockedPeriod.objects.filter(
            supplier=supplier, start_at__lt=end, end_at__gt=start,
        ).exists()

    @staticmethod
    def _covered_by_working_window(*, supplier, start, end) -> bool:
        local_start = timezone.localtime(start)
        local_end = timezone.localtime(end)
        day_of_week = local_start.weekday()

        windows = ProviderWorkingWindow.objects.filter(
            supplier=supplier, day_of_week=day_of_week, is_active=True,
        )
        return any(
            window.start_time <= local_start.time() and local_end.time() <= window.end_time
            for window in windows
        )
