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
