"""Tests for Sprint 7 profiles, organizations, and affiliations."""

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.profiles import (
    AffiliationStatus,
    CaregiverProfile,
    CaregiverProviderType,
    CompanyAffiliationRequest,
    CustomerProfile,
    ElderProfile,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
    PlatformTeamMember,
    TrustedContact,
)
from apps.accounts.services.affiliations import approve_affiliation_request, reject_affiliation_request
from apps.accounts.services.organizations import create_organization_membership, find_organization_by_code_or_name
from apps.accounts.services.profiles import (
    add_trusted_contact,
    calculate_caregiver_profile_completion,
    calculate_customer_profile_completion,
    create_primary_elder_profile,
)
from apps.accounts.services.registration import RegistrationService
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount


class BaseTestCase(TestCase):
    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(slug="salmandyar", defaults={"name": "سالمندیار"})
        for slug in ["customer", "independent_caregiver", "organization_admin", "organization_caregiver"]:
            Role.objects.get_or_create(tenant=self.tenant, slug=slug, defaults={"name": slug, "is_system": True})


class CustomerProfileTest(BaseTestCase):
    def test_customer_creation(self):
        user, profile = RegistrationService.create_customer(phone="09121111111", full_name="Test")
        self.assertEqual(profile.display_name, "Test")
        self.assertEqual(profile.status, "active")

    def test_customer_completion(self):
        user, profile = RegistrationService.create_customer(
            phone="09121111111", full_name="Test", city="tehran", relation_to_elder="child"
        )
        pct = calculate_customer_profile_completion(profile)
        self.assertGreater(pct, 0)

    def test_elder_profile_creation(self):
        user, profile = RegistrationService.create_customer(phone="09121111111", full_name="Test")
        elder = create_primary_elder_profile(customer_profile=profile, full_name="Elder Name", city="tehran")
        self.assertTrue(elder.is_primary)
        self.assertEqual(elder.customer_profile, profile)

    def test_trusted_contact_creation(self):
        user, profile = RegistrationService.create_customer(phone="09121111111", full_name="Test")
        contact = add_trusted_contact(customer_profile=profile, full_name="Brother", phone="09129999999", relation="brother")
        self.assertEqual(contact.customer_profile, profile)
        self.assertTrue(contact.can_receive_sms)


class CaregiverProfileTest(BaseTestCase):
    def test_default_independent(self):
        user, profile, _ = RegistrationService.create_caregiver(phone="09132222222", full_name="CG")
        self.assertEqual(profile.provider_type, CaregiverProviderType.INDEPENDENT)

    def test_completion_calculation(self):
        user, profile, _ = RegistrationService.create_caregiver(
            phone="09132222222", full_name="CG", specialty="nurse", city="tehran"
        )
        pct = calculate_caregiver_profile_completion(profile)
        self.assertGreater(pct, 0)

    def test_affiliation_with_matching_code(self):
        # Create org first
        admin_user, org = RegistrationService.create_company_admin(
            phone="09140000000", admin_name="Admin", company_name="TestOrg"
        )
        user, profile, req = RegistrationService.create_caregiver(
            phone="09132222222", full_name="CG", company_code=org.code
        )
        self.assertIsNotNone(req)
        self.assertEqual(req.organization, org)
        self.assertEqual(req.status, AffiliationStatus.PENDING)

    def test_affiliation_with_unknown_text(self):
        user, profile, req = RegistrationService.create_caregiver(
            phone="09132222222", full_name="CG", company_name="Unknown Company"
        )
        self.assertIsNotNone(req)
        self.assertIsNone(req.organization)
        self.assertEqual(req.requested_company_name_or_code, "Unknown Company")

    def test_approve_converts_to_affiliated(self):
        admin_user, org = RegistrationService.create_company_admin(
            phone="09140000000", admin_name="Admin", company_name="TestOrg"
        )
        user, profile, req = RegistrationService.create_caregiver(
            phone="09132222222", full_name="CG", company_code=org.code
        )
        approve_affiliation_request(request_id=req.id, reviewed_by=admin_user)
        profile.refresh_from_db()
        self.assertEqual(profile.provider_type, CaregiverProviderType.ORGANIZATION_AFFILIATED)
        self.assertTrue(OrganizationMembership.objects.filter(user=user, organization=org).exists())

    def test_reject_keeps_independent(self):
        admin_user, org = RegistrationService.create_company_admin(
            phone="09140000000", admin_name="Admin", company_name="TestOrg"
        )
        user, profile, req = RegistrationService.create_caregiver(
            phone="09132222222", full_name="CG", company_code=org.code
        )
        reject_affiliation_request(request_id=req.id, reviewed_by=admin_user)
        profile.refresh_from_db()
        self.assertEqual(profile.provider_type, CaregiverProviderType.INDEPENDENT)
        req.refresh_from_db()
        self.assertEqual(req.status, AffiliationStatus.REJECTED)


class OrganizationTest(BaseTestCase):
    def test_company_admin_creates_org(self):
        user, org = RegistrationService.create_company_admin(
            phone="09143333333", admin_name="Admin", company_name="My Org"
        )
        self.assertIsNotNone(org)
        self.assertEqual(org.admin_user, user)

    def test_company_admin_creates_membership(self):
        user, org = RegistrationService.create_company_admin(
            phone="09143333333", admin_name="Admin", company_name="My Org"
        )
        membership = OrganizationMembership.objects.filter(user=user, organization=org).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role_type, OrgMembershipRole.ADMIN)

    def test_org_code_unique(self):
        RegistrationService.create_company_admin(phone="09143333333", admin_name="A1", company_name="Org1")
        RegistrationService.create_company_admin(phone="09144444444", admin_name="A2", company_name="Org2")
        codes = list(OrganizationProfile.objects.values_list("code", flat=True))
        self.assertEqual(len(codes), len(set(codes)))

    def test_find_by_code(self):
        _, org = RegistrationService.create_company_admin(phone="09143333333", admin_name="A", company_name="FindMe")
        found = find_organization_by_code_or_name(org.code)
        self.assertEqual(found, org)

    def test_find_by_name(self):
        _, org = RegistrationService.create_company_admin(phone="09143333333", admin_name="A", company_name="FindMe")
        found = find_organization_by_code_or_name("FindMe")
        self.assertEqual(found, org)


class AffiliationIntegrityTest(BaseTestCase):
    def test_cannot_approve_non_pending(self):
        admin_user, org = RegistrationService.create_company_admin(phone="09140000000", admin_name="A", company_name="O")
        _, profile, req = RegistrationService.create_caregiver(phone="09132222222", full_name="CG", company_code=org.code)
        reject_affiliation_request(request_id=req.id, reviewed_by=admin_user)
        with self.assertRaises(ValueError):
            approve_affiliation_request(request_id=req.id, reviewed_by=admin_user)

    def test_cannot_approve_without_org(self):
        _, profile, req = RegistrationService.create_caregiver(phone="09132222222", full_name="CG", company_name="Ghost")
        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09160000000", person=person, tenant=self.tenant)
        with self.assertRaises(ValueError):
            approve_affiliation_request(request_id=req.id, reviewed_by=reviewer)

    def test_no_duplicate_membership(self):
        admin_user, org = RegistrationService.create_company_admin(phone="09140000000", admin_name="A", company_name="O")
        m1, created1 = create_organization_membership(
            organization=org, user=admin_user, role_type=OrgMembershipRole.ADMIN
        )
        m2, created2 = create_organization_membership(
            organization=org, user=admin_user, role_type=OrgMembershipRole.ADMIN
        )
        self.assertTrue(created1 or not created2)
        self.assertEqual(m1.id, m2.id)


class PlatformTeamTest(BaseTestCase):
    def test_seed_demo_idempotent(self):
        from django.core.management import call_command
        call_command("seed_demo_people")
        count1 = UserAccount.objects.count()
        call_command("seed_demo_people")
        count2 = UserAccount.objects.count()
        self.assertEqual(count1, count2)
