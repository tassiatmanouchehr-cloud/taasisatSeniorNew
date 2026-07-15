"""ProfileCompletionService — Phase 1.3 Part A."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile
from apps.accounts.services.profile_completion_service import ProfileCompletionService
from apps.accounts.services.profiles import (
    calculate_caregiver_profile_completion,
    calculate_organization_profile_completion,
)
from apps.kernel.models import Person, Tenant, UserAccount


class _CompletionFixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"completion-{uuid.uuid4().hex[:8]}", name="Completion Test Tenant")

    def _create_caregiver(self, **overrides) -> CaregiverProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Test Caregiver")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        defaults = {"user": user, "person": person, "phone": phone, "display_name": "Test Caregiver"}
        defaults.update(overrides)
        return CaregiverProfile.objects.create(**defaults)

    def _create_organization(self, **overrides) -> OrganizationProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Org Admin")
        admin_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        defaults = {
            "name": "Test Org", "code": f"ORG-{uuid.uuid4().hex[:6].upper()}",
            "admin_user": admin_user, "tenant": self.tenant,
        }
        defaults.update(overrides)
        return OrganizationProfile.objects.create(**defaults)


class CaregiverCompletionTest(_CompletionFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_empty_profile_is_zero_percent_with_all_missing(self):
        caregiver = self._create_caregiver(display_name="", phone="", city="")
        result = ProfileCompletionService.evaluate_caregiver(caregiver)
        self.assertEqual(result.percent, 0)
        self.assertEqual(result.completed, ())
        self.assertEqual(len(result.missing), 7)

    def test_fully_filled_profile_is_100_percent(self):
        caregiver = self._create_caregiver(
            city="tehran", specialty="nurse", bio="Experienced.", years_experience=5, service_radius_km=10,
        )
        result = ProfileCompletionService.evaluate_caregiver(caregiver)
        self.assertEqual(result.percent, 100)
        self.assertEqual(result.missing, ())

    def test_zero_years_experience_counts_as_filled_not_missing(self):
        """A caregiver just starting out (0 years) must not be treated as
        having skipped the field — 0 is a legitimate, filled value."""
        caregiver = self._create_caregiver(
            city="tehran", specialty="nurse", bio="New.", years_experience=0, service_radius_km=0,
        )
        result = ProfileCompletionService.evaluate_caregiver(caregiver)
        self.assertEqual(result.percent, 100)

    def test_missing_years_experience_is_reported_by_label(self):
        caregiver = self._create_caregiver(
            city="tehran", specialty="nurse", bio="Experienced.", years_experience=None, service_radius_km=10,
        )
        result = ProfileCompletionService.evaluate_caregiver(caregiver)
        self.assertIn("سابقه کار", result.missing)
        self.assertLess(result.percent, 100)

    def test_deterministic_and_idempotent(self):
        caregiver = self._create_caregiver(city="tehran", specialty="nurse")
        first = ProfileCompletionService.evaluate_caregiver(caregiver)
        second = ProfileCompletionService.evaluate_caregiver(caregiver)
        self.assertEqual(first, second)

    def test_bare_int_helper_matches_structured_result(self):
        caregiver = self._create_caregiver(city="tehran", specialty="nurse", bio="x", years_experience=1, service_radius_km=1)
        structured = ProfileCompletionService.evaluate_caregiver(caregiver)
        self.assertEqual(calculate_caregiver_profile_completion(caregiver), structured.percent)


class OrganizationCompletionTest(_CompletionFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_empty_profile_is_low_percent(self):
        organization = self._create_organization(city="", phone="", address="", description="", company_type="")
        result = ProfileCompletionService.evaluate_organization(organization)
        self.assertLess(result.percent, 100)
        self.assertIn("شهر", result.missing)

    def test_fully_filled_profile_is_100_percent(self):
        organization = self._create_organization(
            city="tehran", phone="09120000000", address="Some address",
            description="A senior-care company.", company_type="home_care",
        )
        result = ProfileCompletionService.evaluate_organization(organization)
        self.assertEqual(result.percent, 100)
        self.assertEqual(result.missing, ())

    def test_deterministic_and_idempotent(self):
        organization = self._create_organization(city="tehran")
        first = ProfileCompletionService.evaluate_organization(organization)
        second = ProfileCompletionService.evaluate_organization(organization)
        self.assertEqual(first, second)

    def test_bare_int_helper_matches_structured_result(self):
        organization = self._create_organization(
            city="tehran", phone="09120000000", address="addr", description="desc", company_type="type",
        )
        structured = ProfileCompletionService.evaluate_organization(organization)
        self.assertEqual(calculate_organization_profile_completion(organization), structured.percent)


class DifferentRequiredFieldsTest(_CompletionFixtureMixin, TestCase):
    """Caregiver and organization have distinct field sets — Requirement 3."""

    def setUp(self):
        self._build_fixture()

    def test_caregiver_and_organization_field_sets_differ(self):
        from apps.accounts.services.profile_completion_service import (
            CAREGIVER_COMPLETION_FIELDS,
            ORGANIZATION_COMPLETION_FIELDS,
        )

        caregiver_fields = {name for name, _ in CAREGIVER_COMPLETION_FIELDS}
        organization_fields = {name for name, _ in ORGANIZATION_COMPLETION_FIELDS}
        self.assertNotEqual(caregiver_fields, organization_fields)
