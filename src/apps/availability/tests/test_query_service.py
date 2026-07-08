"""
Tests for AvailabilityQueryService: working-window availability, blocked
periods overriding working windows, overlapping blocked periods, and
timezone-aware datetime handling.
"""

import datetime as dt

from django.utils import timezone

from apps.availability.models import BlockedPeriodReason
from apps.availability.services import AvailabilityError, AvailabilityMutationService, AvailabilityQueryService

from .helpers import AvailabilityTestCase


def _next_weekday(target_weekday: int) -> dt.date:
    """Return the next date (today or later) whose .weekday() == target_weekday."""
    today = timezone.localdate()
    delta = (target_weekday - today.weekday()) % 7
    return today + dt.timedelta(days=delta)


class AvailabilityQueryServiceTest(AvailabilityTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = self._create_supplier()
        self.monday = _next_weekday(0)
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time=dt.time(9, 0), end_time=dt.time(17, 0),
        )

    def _aware(self, date_, hour, minute=0):
        return timezone.make_aware(dt.datetime.combine(date_, dt.time(hour, minute)))

    def test_available_within_working_window(self):
        self.assertTrue(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 10), end=self._aware(self.monday, 11),
            ),
        )

    def test_unavailable_outside_working_window(self):
        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 18), end=self._aware(self.monday, 19),
            ),
        )

    def test_unavailable_when_request_partially_exceeds_window(self):
        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 16), end=self._aware(self.monday, 18),
            ),
        )

    def test_unavailable_on_day_with_no_configured_window(self):
        tuesday = _next_weekday(1)
        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(tuesday, 10), end=self._aware(tuesday, 11),
            ),
        )

    def test_unavailable_by_default_with_no_windows_configured_at_all(self):
        bare_supplier = self._create_supplier(display_name="No Schedule")
        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(
                supplier=bare_supplier, start=self._aware(self.monday, 10), end=self._aware(self.monday, 11),
            ),
        )

    def test_blocked_period_overrides_working_window(self):
        AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier,
            start_at=self._aware(self.monday, 10),
            end_at=self._aware(self.monday, 12),
            reason=BlockedPeriodReason.LEAVE,
        )

        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 10, 30), end=self._aware(self.monday, 11),
            ),
        )
        # Still available outside the blocked slice but inside the working window.
        self.assertTrue(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 13), end=self._aware(self.monday, 14),
            ),
        )

    def test_overlapping_blocked_periods_both_apply(self):
        AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier, start_at=self._aware(self.monday, 10), end_at=self._aware(self.monday, 12),
        )
        AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier, start_at=self._aware(self.monday, 11), end_at=self._aware(self.monday, 13),
        )

        self.assertEqual(
            AvailabilityQueryService.get_blocked_periods(
                supplier=self.supplier, start=self._aware(self.monday, 0), end=self._aware(self.monday, 23),
            ).count(),
            2,
        )
        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 11, 30), end=self._aware(self.monday, 12, 30),
            ),
        )

    def test_naive_datetime_raises_availability_error(self):
        naive_start = dt.datetime.combine(self.monday, dt.time(10, 0))
        naive_end = dt.datetime.combine(self.monday, dt.time(11, 0))
        with self.assertRaises(AvailabilityError):
            AvailabilityQueryService.is_supplier_available(supplier=self.supplier, start=naive_start, end=naive_end)

    def test_start_after_end_raises_availability_error(self):
        with self.assertRaises(AvailabilityError):
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 11), end=self._aware(self.monday, 10),
            )

    def test_range_spanning_local_midnight_raises_availability_error(self):
        tuesday = self.monday + dt.timedelta(days=1)
        with self.assertRaises(AvailabilityError):
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=self._aware(self.monday, 23), end=self._aware(tuesday, 1),
            )

    def test_utc_datetime_is_converted_to_local_time_for_window_matching(self):
        """A UTC-aware datetime that lands on a different local calendar day/hour
        must still be evaluated against the supplier's local working window."""
        # 06:30 local (Asia/Tehran, UTC+03:30) on Monday == 03:00 UTC on Monday.
        local_naive = dt.datetime.combine(self.monday, dt.time(6, 30))
        local_aware = timezone.make_aware(local_naive)
        utc_start = local_aware.astimezone(dt.timezone.utc)
        utc_end = utc_start + dt.timedelta(hours=1)

        # 06:30-07:30 local is before the 09:00 window opens.
        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(supplier=self.supplier, start=utc_start, end=utc_end),
        )

        # Shifting 3 hours later lands inside the window when interpreted locally.
        self.assertTrue(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.supplier, start=utc_start + dt.timedelta(hours=3), end=utc_end + dt.timedelta(hours=3),
            ),
        )
