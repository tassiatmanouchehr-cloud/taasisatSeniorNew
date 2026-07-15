"""Availability management via the provider portal — Epic 02, extended in
Sprint 2.4 (Caregiver Availability and Working Schedule)."""

from django.utils import timezone

from apps.kernel.models import Person, UserAccount

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


    def test_add_working_window_rejects_duplicate(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.login_as_provider()
        response = self.client.post("/provider/availability/", {
            "day_of_week": "0", "start_time": "09:00", "end_time": "17:00",
        })
        self.assertEqual(response.status_code, 200)

        from apps.availability.models import ProviderWorkingWindow

        self.assertEqual(ProviderWorkingWindow.objects.filter(supplier=self.supplier).count(), 1)

    def test_add_working_window_rejects_overlap(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.login_as_provider()
        response = self.client.post("/provider/availability/", {
            "day_of_week": "0", "start_time": "16:00", "end_time": "20:00",
        })
        self.assertEqual(response.status_code, 200)

        from apps.availability.models import ProviderWorkingWindow

        self.assertEqual(ProviderWorkingWindow.objects.filter(supplier=self.supplier).count(), 1)

    def test_owner_can_update_working_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.login_as_provider()
        response = self.client.post(f"/provider/availability/windows/{window.id}/update/", {
            "start_time": "10:00", "end_time": "18:00",
        })
        self.assertRedirects(response, "/provider/availability/")

        from apps.availability.models import ProviderWorkingWindow

        updated = ProviderWorkingWindow.objects.get(id=window.id)
        self.assertEqual(str(updated.start_time), "10:00:00")

    def test_another_provider_cannot_update_working_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/availability/windows/{window.id}/update/", {
            "start_time": "10:00", "end_time": "18:00",
        })
        self.assertEqual(response.status_code, 404)

        from apps.availability.models import ProviderWorkingWindow

        unchanged = ProviderWorkingWindow.objects.get(id=window.id)
        self.assertEqual(str(unchanged.start_time), "09:00:00")

    def test_cross_tenant_cannot_update_working_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.client.force_login(self.other_tenant_provider_user)
        response = self.client.post(f"/provider/availability/windows/{window.id}/update/", {
            "start_time": "10:00", "end_time": "18:00",
        })
        self.assertEqual(response.status_code, 404)

    def test_customer_cannot_access_availability_page(self):
        self.client.force_login(self.customer.user)
        response = self.client.get("/provider/availability/")
        self.assertEqual(response.status_code, 403)

    def test_customer_cannot_toggle_working_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.client.force_login(self.customer.user)
        response = self.client.post(f"/provider/availability/windows/{window.id}/toggle/")
        self.assertEqual(response.status_code, 403)

        from apps.availability.models import ProviderWorkingWindow

        unchanged = ProviderWorkingWindow.objects.get(id=window.id)
        self.assertTrue(unchanged.is_active)

    def test_unrelated_organization_user_cannot_mutate_availability(self):
        """An account with no caregiver_profile at all (e.g. an
        organization-only user) — _guard() denies it 403 before any
        service call, the same pattern Sprint 2.3 established for skills."""
        import uuid as uuid_module

        person = Person.objects.create(tenant=self.tenant, full_name="Org User")
        org_user = UserAccount.objects.create_user(
            phone=f"0912{uuid_module.uuid4().hex[:7]}", person=person, tenant=self.tenant,
        )
        self.client.force_login(org_user)
        response = self.client.get("/provider/availability/")
        self.assertEqual(response.status_code, 403)

    def test_owner_can_toggle_working_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.login_as_provider()
        response = self.client.post(f"/provider/availability/windows/{window.id}/toggle/")
        self.assertRedirects(response, "/provider/availability/")

        from apps.availability.models import ProviderWorkingWindow

        self.assertFalse(ProviderWorkingWindow.objects.get(id=window.id).is_active)

    def test_another_provider_cannot_toggle_working_window(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/availability/windows/{window.id}/toggle/")
        self.assertEqual(response.status_code, 404)

        from apps.availability.models import ProviderWorkingWindow

        self.assertTrue(ProviderWorkingWindow.objects.get(id=window.id).is_active)


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

    def test_add_blocked_period_rejects_invalid_range(self):
        self.login_as_provider()
        start = timezone.now() + timezone.timedelta(days=1)
        end = start - timezone.timedelta(hours=2)
        self.client.post("/provider/availability/blocked-periods/add/", {
            "start_at": start.isoformat(), "end_at": end.isoformat(), "reason": "SICK",
        })

        from apps.availability.models import AvailabilityBlockedPeriod

        self.assertFalse(AvailabilityBlockedPeriod.objects.filter(supplier=self.supplier).exists())

    def test_cannot_remove_another_providers_blocked_period(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=2)
        period = AvailabilityMutationService.add_blocked_period(supplier=self.supplier, start_at=start, end_at=end)

        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/availability/blocked-periods/{period.id}/remove/")
        self.assertEqual(response.status_code, 404)

    def test_customer_cannot_add_blocked_period(self):
        self.client.force_login(self.customer.user)
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=2)
        response = self.client.post("/provider/availability/blocked-periods/add/", {
            "start_at": start.isoformat(), "end_at": end.isoformat(), "reason": "SICK",
        })
        self.assertEqual(response.status_code, 403)


class AvailabilityPublicSummaryPreviewTest(ProviderPortalTestCase):
    def test_public_summary_reflects_active_windows_only(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time="09:00", end_time="17:00",
        )
        self.login_as_provider()
        response = self.client.get("/provider/availability/")
        self.assertContains(response, "دوشنبه")

    def test_public_summary_empty_state_when_no_active_windows(self):
        self.login_as_provider()
        response = self.client.get("/provider/availability/")
        self.assertContains(response, "هنوز ساعت کاری فعالی")


class AvailabilityQueryCountTest(ProviderPortalTestCase):
    def test_availability_page_query_count_bounded(self):
        from apps.availability.services.mutation_service import AvailabilityMutationService

        for day in range(3):
            AvailabilityMutationService.add_working_window(
                supplier=self.supplier, day_of_week=day, start_time="09:00", end_time="17:00",
            )
        start = timezone.now() + timezone.timedelta(days=1)
        AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier, start_at=start, end_at=start + timezone.timedelta(hours=2),
        )
        self.login_as_provider()
        # Fixed-cost page: session/auth resolution + working windows +
        # blocked periods + capacity engagement count + capacity rule lookup
        # + public-summary distinct-days query — bounded regardless of how
        # many windows/blocked periods exist (no per-item query).
        with self.assertNumQueries(9):
            self.client.get("/provider/availability/")
