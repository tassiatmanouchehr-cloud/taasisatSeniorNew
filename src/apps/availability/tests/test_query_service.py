"""
Tests for AvailabilityQueryService: working-window availability, blocked
periods overriding working windows, overlapping blocked periods, and
timezone-aware datetime handling.
"""

import datetime as dt

from django.utils import timezone

from apps.availability.models import BlockedPeriodReason
from apps.availability.services import (
    AvailabilityError,
    AvailabilityMutationService,
    AvailabilityQueryService,
)

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


class AvailabilityEvaluateTest(AvailabilityTestCase):
    """Structured evaluate() — Sprint 2.4. is_supplier_available() is now a
    thin wrapper around this; these tests cover the structured fields it
    adds (reasons, matched_window, conflicting_blocked_period, timezone)."""

    def setUp(self):
        super().setUp()
        self.supplier = self._create_supplier()
        self.monday = _next_weekday(0)
        self.window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time=dt.time(9, 0), end_time=dt.time(17, 0),
        )

    def _aware(self, date_, hour, minute=0):
        return timezone.make_aware(dt.datetime.combine(date_, dt.time(hour, minute)))

    def test_evaluate_available_reports_matched_window(self):
        result = AvailabilityQueryService.evaluate(
            supplier=self.supplier, start=self._aware(self.monday, 10), end=self._aware(self.monday, 11),
        )
        self.assertTrue(result.available)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.matched_window.id, self.window.id)
        self.assertIsNone(result.conflicting_blocked_period)
        self.assertTrue(result.timezone)

    def test_evaluate_unavailable_no_window_reports_reason(self):
        tuesday = _next_weekday(1)
        result = AvailabilityQueryService.evaluate(
            supplier=self.supplier, start=self._aware(tuesday, 10), end=self._aware(tuesday, 11),
        )
        self.assertFalse(result.available)
        self.assertEqual(result.reasons, ("no_matching_working_window",))
        self.assertIsNone(result.matched_window)
        self.assertIsNone(result.conflicting_blocked_period)

    def test_evaluate_blocked_period_reports_conflict(self):
        blocked = AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier,
            start_at=self._aware(self.monday, 10),
            end_at=self._aware(self.monday, 12),
        )
        result = AvailabilityQueryService.evaluate(
            supplier=self.supplier, start=self._aware(self.monday, 10, 30), end=self._aware(self.monday, 11),
        )
        self.assertFalse(result.available)
        self.assertEqual(result.reasons, ("blocked_period",))
        self.assertEqual(result.conflicting_blocked_period.id, blocked.id)
        self.assertIsNone(result.matched_window)

    def test_evaluate_is_read_only(self):
        """evaluate() must never create, mutate, or delete rows."""
        from apps.availability.models import AvailabilityBlockedPeriod, ProviderWorkingWindow

        window_count_before = ProviderWorkingWindow.objects.count()
        blocked_count_before = AvailabilityBlockedPeriod.objects.count()
        AvailabilityQueryService.evaluate(
            supplier=self.supplier, start=self._aware(self.monday, 10), end=self._aware(self.monday, 11),
        )
        self.assertEqual(ProviderWorkingWindow.objects.count(), window_count_before)
        self.assertEqual(AvailabilityBlockedPeriod.objects.count(), blocked_count_before)

    def test_evaluate_timezone_is_deterministic(self):
        result_1 = AvailabilityQueryService.evaluate(
            supplier=self.supplier, start=self._aware(self.monday, 10), end=self._aware(self.monday, 11),
        )
        result_2 = AvailabilityQueryService.evaluate(
            supplier=self.supplier, start=self._aware(self.monday, 10), end=self._aware(self.monday, 11),
        )
        self.assertEqual(result_1.timezone, result_2.timezone)


class DistinctActiveDaysTest(AvailabilityTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = self._create_supplier()

    def test_no_windows_returns_empty(self):
        self.assertEqual(AvailabilityQueryService.get_distinct_active_days(supplier=self.supplier), ())

    def test_returns_sorted_distinct_days(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=3, start_time=dt.time(8, 0), end_time=dt.time(12, 0),
        )
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time=dt.time(8, 0), end_time=dt.time(12, 0),
        )
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time=dt.time(13, 0), end_time=dt.time(17, 0),
        )
        self.assertEqual(AvailabilityQueryService.get_distinct_active_days(supplier=self.supplier), (0, 3))

    def test_disabled_window_day_excluded(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=1, start_time=dt.time(8, 0), end_time=dt.time(12, 0),
        )
        AvailabilityMutationService.update_working_window(window_id=window.id, is_active=False)
        self.assertEqual(AvailabilityQueryService.get_distinct_active_days(supplier=self.supplier), ())
