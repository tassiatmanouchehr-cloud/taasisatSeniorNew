"""HTTP-level tests for the Epic 06 public views.

Tests run against the platform's real default tenant (TenantService
.get_default_tenant()) rather than an isolated per-test tenant, because
the views never accept a tenant_id — they always resolve it via
TenantService, exactly like every other unauthenticated view in this
codebase (apps.accounts.services.registration). This is the one place in
this test suite where that matters: the service-level tests above use
isolated tenants and pass tenant_id explicitly instead."""

import uuid

from django.test import TestCase
from django.urls import reverse

from apps.kernel.services.tenant_service import TenantService

from .helpers import PublicSiteTestCase


class HomeViewTest(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertEqual(response.status_code, 200)


class FindACaregiverViewTest(PublicSiteTestCase):
    def setUp(self):
        super().setUp()
        # Views always resolve the default tenant — build fixtures there too.
        self.default_tenant = TenantService.get_default_tenant()
        self.tenant = self.default_tenant

    def test_directory_page_returns_200(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"))
        self.assertEqual(response.status_code, 200)

    def test_directory_page_lists_real_caregiver(self):
        self._create_caregiver_supplier(display_name="مریم احمدی تست")

        response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertContains(response, "مریم احمدی تست")

    def test_city_filter_via_querystring(self):
        self._create_caregiver_supplier(display_name="تهرانی تست", city="tehran")
        self._create_caregiver_supplier(display_name="مشهدی تست", city="mashhad")

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"city": "mashhad"})

        self.assertContains(response, "مشهدی تست")
        self.assertNotContains(response, "تهرانی تست")

    def test_invalid_supplier_type_query_param_is_ignored_not_a_500(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"type": "not-a-real-type"})
        self.assertEqual(response.status_code, 200)


class CaregiverProfileViewTest(PublicSiteTestCase):
    def setUp(self):
        super().setUp()
        self.default_tenant = TenantService.get_default_tenant()
        self.tenant = self.default_tenant

    def test_profile_page_returns_200_for_real_caregiver(self):
        supplier, _ = self._create_caregiver_supplier(display_name="نگار حسینی تست")

        response = self.client.get(reverse("public_site:caregiver-profile", args=[supplier.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نگار حسینی تست")

    def test_unknown_supplier_returns_404(self):
        response = self.client.get(reverse("public_site:caregiver-profile", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_non_uuid_path_segment_returns_404(self):
        response = self.client.get("/find-a-caregiver/not-a-uuid/")
        self.assertEqual(response.status_code, 404)

    def test_existing_join_as_caregiver_marketing_page_still_works(self):
        """Regression guard: /caregivers/ (the pre-existing 'join as a
        caregiver' recruiting page) must remain untouched by the new
        /find-a-caregiver/ directory routes."""
        response = self.client.get(reverse("public_site:caregivers"))
        self.assertEqual(response.status_code, 200)
