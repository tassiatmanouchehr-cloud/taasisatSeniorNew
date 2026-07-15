"""Tests for registration service."""

from django.test import TestCase

from apps.accounts.models.profiles import (
    AffiliationStatus,
    CaregiverProfile,
    CaregiverProviderType,
    CompanyAffiliationRequest,
    CustomerProfile,
    OrganizationProfile,
    ProfileStatus,
)
from apps.accounts.services.registration import RegistrationService
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount


class CustomerRegistrationTest(TestCase):
    """Test customer account creation."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar", defaults={"name": "سالمندیار"}
        )
        Role.objects.get_or_create(
            tenant=self.tenant, slug="customer",
            defaults={"name": "مشتری", "is_system": True},
        )

    def test_creates_person_user_profile(self):
        user, profile = RegistrationService.create_customer(
            phone="09121234567",
            full_name="فاطمه رضایی",
            city="tehran",
            relation_to_elder="child",
        )
        self.assertIsNotNone(user)
        self.assertIsNotNone(profile)
        self.assertEqual(user.phone, "09121234567")
        self.assertEqual(profile.display_name, "فاطمه رضایی")
        self.assertEqual(profile.city, "tehran")
        # Verify Person created
        self.assertIsNotNone(user.person)
        self.assertEqual(user.person.full_name, "فاطمه رضایی")

    def test_assigns_customer_role(self):
        user, _ = RegistrationService.create_customer(
            phone="09121234567", full_name="Test"
        )
        assignment = RoleAssignment.objects.filter(user=user).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.role.slug, "customer")


class CaregiverRegistrationTest(TestCase):
    """Test caregiver account creation."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar", defaults={"name": "سالمندیار"}
        )
        Role.objects.get_or_create(
            tenant=self.tenant, slug="independent_caregiver",
            defaults={"name": "مراقب مستقل", "is_system": True},
        )

    def test_creates_independent_caregiver(self):
        user, profile, affiliation = RegistrationService.create_caregiver(
            phone="09129876543",
            full_name="مریم احمدی",
            specialty="nurse",
            city="isfahan",
        )
        self.assertEqual(profile.provider_type, CaregiverProviderType.INDEPENDENT)
        self.assertIsNone(affiliation)

    def test_new_caregiver_registration_creates_a_draft_profile(self):
        """Phase 1.3 remediation: a freshly registered caregiver must not
        start ACTIVE — activation is now an explicit, platform-staff-gated
        action (ProfileActivationService)."""
        _, profile, _ = RegistrationService.create_caregiver(
            phone="09129876543", full_name="مریم احمدی",
        )
        self.assertEqual(profile.status, ProfileStatus.DRAFT)

    def test_assigns_independent_caregiver_role(self):
        user, _, _ = RegistrationService.create_caregiver(
            phone="09129876543", full_name="Test"
        )
        assignment = RoleAssignment.objects.filter(user=user).first()
        self.assertEqual(assignment.role.slug, "independent_caregiver")

    def test_creates_affiliation_request_with_company_code(self):
        user, profile, affiliation = RegistrationService.create_caregiver(
            phone="09129876543",
            full_name="مریم احمدی",
            company_code="TEST-1234",
        )
        self.assertIsNotNone(affiliation)
        self.assertEqual(affiliation.status, AffiliationStatus.PENDING)
        self.assertEqual(affiliation.requested_company_name_or_code, "TEST-1234")
        # Caregiver still independent
        self.assertEqual(profile.provider_type, CaregiverProviderType.INDEPENDENT)

    def test_creates_affiliation_request_with_company_name(self):
        user, profile, affiliation = RegistrationService.create_caregiver(
            phone="09129876543",
            full_name="Test",
            company_name="آژانس مراقبت نور",
        )
        self.assertIsNotNone(affiliation)
        self.assertEqual(
            affiliation.requested_company_name_or_code, "آژانس مراقبت نور"
        )


class CompanyAdminRegistrationTest(TestCase):
    """Test company admin account creation."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar", defaults={"name": "سالمندیار"}
        )
        Role.objects.get_or_create(
            tenant=self.tenant, slug="organization_admin",
            defaults={"name": "مدیر سازمان", "is_system": True},
        )

    def test_creates_organization(self):
        user, org = RegistrationService.create_company_admin(
            phone="09131112222",
            admin_name="محمد کریمی",
            company_name="شرکت مراقبتی نور",
            company_type="care_agency",
            city="tehran",
            team_size="6-20",
        )
        self.assertIsNotNone(org)
        self.assertEqual(org.name, "شرکت مراقبتی نور")
        self.assertEqual(org.admin_user, user)
        self.assertTrue(org.code)  # Generated code
        self.assertEqual(org.company_type, "care_agency")

    def test_new_organization_registration_creates_a_draft_profile(self):
        """Phase 1.3 remediation: a freshly registered organization must
        not start ACTIVE — activation is now an explicit, platform-staff-
        gated action (ProfileActivationService)."""
        _, org = RegistrationService.create_company_admin(
            phone="09131112222", admin_name="محمد کریمی", company_name="شرکت مراقبتی نور",
        )
        self.assertEqual(org.status, ProfileStatus.DRAFT)

    def test_assigns_organization_admin_role(self):
        user, _ = RegistrationService.create_company_admin(
            phone="09131112222",
            admin_name="Test",
            company_name="Test Org",
        )
        assignment = RoleAssignment.objects.filter(user=user).first()
        self.assertEqual(assignment.role.slug, "organization_admin")
