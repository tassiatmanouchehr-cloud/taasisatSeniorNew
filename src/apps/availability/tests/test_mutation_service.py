"""Tests for AvailabilityMutationService: add/update/remove windows and blocked periods."""

import datetime as dt

from django.utils import timezone

from apps.availability.models import AvailabilityBlockedPeriod, ProviderWorkingWindow
from apps.availability.services import AvailabilityError, AvailabilityMutationService

from .helpers import AvailabilityTestCase


class AvailabilityMutationServiceTest(AvailabilityTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = self._create_supplier()

    def test_add_working_window(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        self.assertEqual(window.day_of_week, 2)
        self.assertTrue(window.is_active)

    def test_add_working_window_rejects_start_after_end(self):
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.add_working_window(
                supplier=self.supplier, day_of_week=2, start_time=dt.time(16, 0), end_time=dt.time(8, 0),
            )

    def test_update_working_window(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        updated = AvailabilityMutationService.update_working_window(
            window_id=window.id, start_time=dt.time(9, 0), end_time=dt.time(17, 0),
        )
        self.assertEqual(updated.start_time, dt.time(9, 0))
        self.assertEqual(updated.end_time, dt.time(17, 0))

    def test_update_working_window_rejects_invalid_range(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.update_working_window(window_id=window.id, start_time=dt.time(20, 0))

    def test_update_working_window_can_deactivate(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        updated = AvailabilityMutationService.update_working_window(window_id=window.id, is_active=False)
        self.assertFalse(updated.is_active)

    def test_remove_working_window(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        AvailabilityMutationService.remove_working_window(window_id=window.id)
        self.assertFalse(ProviderWorkingWindow.objects.filter(id=window.id).exists())

    def test_add_blocked_period(self):
        start = timezone.now()
        end = start + dt.timedelta(hours=2)
        blocked = AvailabilityMutationService.add_blocked_period(supplier=self.supplier, start_at=start, end_at=end)
        self.assertEqual(blocked.supplier_id, self.supplier.id)

    def test_add_blocked_period_rejects_naive_datetimes(self):
        naive_start = dt.datetime.now()
        naive_end = naive_start + dt.timedelta(hours=1)
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.add_blocked_period(supplier=self.supplier, start_at=naive_start, end_at=naive_end)

    def test_add_blocked_period_rejects_start_after_end(self):
        start = timezone.now()
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.add_blocked_period(
                supplier=self.supplier, start_at=start, end_at=start - dt.timedelta(hours=1),
            )

    def test_remove_blocked_period(self):
        start = timezone.now()
        blocked = AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier, start_at=start, end_at=start + dt.timedelta(hours=1),
        )
        AvailabilityMutationService.remove_blocked_period(blocked_period_id=blocked.id)
        self.assertFalse(AvailabilityBlockedPeriod.objects.filter(id=blocked.id).exists())

    def test_add_working_window_rejects_exact_duplicate(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.add_working_window(
                supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
            )

    def test_add_working_window_rejects_partial_overlap(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.add_working_window(
                supplier=self.supplier, day_of_week=2, start_time=dt.time(15, 0), end_time=dt.time(18, 0),
            )

    def test_add_working_window_allows_adjacent_non_overlapping(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(12, 0),
        )
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(12, 0), end_time=dt.time(16, 0),
        )
        self.assertEqual(window.start_time, dt.time(12, 0))

    def test_add_working_window_allows_different_day_same_time(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=3, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        self.assertEqual(window.day_of_week, 3)

    def test_add_working_window_allows_overlap_with_disabled_window(self):
        disabled = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        AvailabilityMutationService.update_working_window(window_id=disabled.id, is_active=False)
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(9, 0), end_time=dt.time(17, 0),
        )
        self.assertTrue(window.is_active)

    def test_add_working_window_allows_overlap_for_different_supplier(self):
        other_supplier = self._create_supplier()
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        window = AvailabilityMutationService.add_working_window(
            supplier=other_supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        self.assertEqual(window.supplier_id, other_supplier.id)

    def test_update_working_window_rejects_overlap_with_another_window(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(12, 0),
        )
        second = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(13, 0), end_time=dt.time(17, 0),
        )
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.update_working_window(window_id=second.id, start_time=dt.time(11, 0))

    def test_update_working_window_allows_no_op_overlap_with_self(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        updated = AvailabilityMutationService.update_working_window(window_id=window.id, start_time=dt.time(8, 30))
        self.assertEqual(updated.start_time, dt.time(8, 30))

    def test_update_working_window_reactivation_checks_overlap(self):
        first = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(12, 0),
        )
        second = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(13, 0), end_time=dt.time(17, 0),
        )
        # Disable, then retime while disabled (no overlap check applies to a
        # disabled window), then attempt to reactivate into the now-overlapping slot.
        AvailabilityMutationService.update_working_window(window_id=second.id, is_active=False)
        AvailabilityMutationService.update_working_window(
            window_id=second.id, start_time=dt.time(9, 0), end_time=dt.time(11, 0), is_active=False,
        )
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.update_working_window(window_id=second.id, is_active=True)
        self.assertTrue(ProviderWorkingWindow.objects.get(id=first.id).is_active)
        self.assertFalse(ProviderWorkingWindow.objects.get(id=second.id).is_active)

    def test_toggle_working_window_disables_then_enables(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=2, start_time=dt.time(8, 0), end_time=dt.time(16, 0),
        )
        disabled = AvailabilityMutationService.toggle_working_window(window=window)
        self.assertFalse(disabled.is_active)
        enabled = AvailabilityMutationService.toggle_working_window(window=disabled)
        self.assertTrue(enabled.is_active)

    def test_overlapping_blocked_periods_still_both_allowed(self):
        """Pre-existing, tested repository convention (see
        test_query_service.py::test_overlapping_blocked_periods_both_apply)
        — overlapping blocked periods are harmless and must keep coexisting;
        this sprint deliberately does not add overlap refusal for them."""
        start = timezone.now()
        first = AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier, start_at=start, end_at=start + dt.timedelta(hours=2),
        )
        second = AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier, start_at=start + dt.timedelta(hours=1), end_at=start + dt.timedelta(hours=3),
        )
        self.assertEqual(AvailabilityBlockedPeriod.objects.filter(supplier=self.supplier).count(), 2)
        self.assertNotEqual(first.id, second.id)
