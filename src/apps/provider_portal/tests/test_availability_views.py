"""Availability management via the provider portal — Epic 02."""

from django.utils import timezone

from .helpers import ProviderPortalTestCase


class WorkingWindowViewTest(ProviderPortalTestCase):
    def test_add_working_window(self):
        self.login_as_provider()
        response = self.client.post("/provider/availability/", {
            "day_of_week": "0", "start_time": "09:00", "end_time": "17:00",
        })
        self.assertRedirects(response, "/provider/availability/")

        from apps.availability.models import ProviderWorkingWindow

        self.assertTrue(ProviderWorkingWindow.objects.filter(supplier=self.supplier).exists())

    def test_add_working_window_rejects_end_before_start(self):
        self.login_as_provider()
        response = self.client.post("/provider/availability/", {
            "day_of_week": "0", "start_time": "17:00", "end_time": "09:00",
        })
        self.assertEqual(response.status_code, 200)

        from apps.availability.models import ProviderWorkingWindow

        self.assertFalse(ProviderWorkingWindow.objects.filter(supplier=self.supplier).exists())

    def test_remove_working_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.login_as_provider()
        response = self.client.post(f"/provider/availability/windows/{window.id}/remove/")
        self.assertRedirects(response, "/provider/availability/")

        from apps.availability.models import ProviderWorkingWindow

        self.assertFalse(ProviderWorkingWindow.objects.filter(id=window.id).exists())

    def test_cannot_remove_another_providers_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/availability/windows/{window.id}/remove/")
        self.assertEqual(response.status_code, 404)

        from apps.availability.models import ProviderWorkingWindow

        self.assertTrue(ProviderWorkingWindow.objects.filter(id=window.id).exists())


class BlockedPeriodViewTest(ProviderPortalTestCase):
    def test_add_blocked_period(self):
        self.login_as_provider()
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=2)
        response = self.client.post("/provider/availability/blocked-periods/add/", {
            "start_at": start.isoformat(), "end_at": end.isoformat(), "reason": "SICK",
        })
        self.assertRedirects(response, "/provider/availability/")

        from apps.availability.models import AvailabilityBlockedPeriod

        self.assertTrue(AvailabilityBlockedPeriod.objects.filter(supplier=self.supplier).exists())

    def test_cannot_remove_another_providers_blocked_period(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=2)
        period = AvailabilityMutationService.add_blocked_period(supplier=self.supplier, start_at=start, end_at=end)

        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/availability/blocked-periods/{period.id}/remove/")
        self.assertEqual(response.status_code, 404)
