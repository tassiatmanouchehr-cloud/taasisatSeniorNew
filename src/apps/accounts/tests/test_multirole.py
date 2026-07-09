"""
Tests for Module 21A — multi-role account model and demo account seeding.

Covers: one person holding both caregiver and customer profiles on the
same UserAccount, idempotent profile-attachment helpers, no duplicate
UserAccount/Person needed for multi-role identity, and the
seed_demo_accounts management command.
"""

import uuid

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, CustomerProfile
from apps.accounts.services.profiles import ensure_caregiver_profile, ensure_customer_profile
from apps.kernel.models import Person, RoleAssignment, Tenant, UserAccount


class MultiRoleIdentityTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
        self.person = Person.objects.create(tenant=self.tenant, full_name="Maryam Ahmadi")
        self.user = UserAccount.objects.create_user(
            email="maryam@example.com", person=self.person, tenant=self.tenant,
        )

    def test_one_person_can_have_caregiver_and_customer_profiles(self):
        caregiver_profile = ensure_caregiver_profile(self.user)
        customer_profile = ensure_customer_profile(self.user)

        self.assertEqual(CaregiverProfile.objects.filter(user=self.user).count(), 1)
        self.assertEqual(CustomerProfile.objects.filter(user=self.user).count(), 1)
        self.assertEqual(caregiver_profile.person_id, self.person.id)
        self.assertEqual(customer_profile.person_id, self.person.id)

    def test_caregiver_can_act_as_customer_at_data_model_level(self):
        ensure_caregiver_profile(self.user)
        ensure_customer_profile(self.user)

        # The same UserAccount now resolves to both roles' data.
        self.user.refresh_from_db()
        self.assertTrue(hasattr(self.user, "caregiver_profile"))
        self.assertTrue(hasattr(self.user, "customer_profile"))

    def test_no_duplicate_useraccount_needed_for_multirole_identity(self):
        ensure_caregiver_profile(self.user)
        ensure_customer_profile(self.user)

        self.assertEqual(UserAccount.objects.filter(person=self.person).count(), 1)
        self.assertEqual(Person.objects.filter(id=self.person.id).count(), 1)

    def test_ensure_customer_profile_is_idempotent(self):
        first = ensure_customer_profile(self.user)
        second = ensure_customer_profile(self.user)
        self.assertEqual(first.id, second.id)
        self.assertEqual(CustomerProfile.objects.filter(user=self.user).count(), 1)

    def test_ensure_caregiver_profile_is_idempotent(self):
        first = ensure_caregiver_profile(self.user)
        second = ensure_caregiver_profile(self.user)
        self.assertEqual(first.id, second.id)
        self.assertEqual(CaregiverProfile.objects.filter(user=self.user).count(), 1)

    def test_ensure_customer_profile_assigns_customer_role(self):
        from apps.kernel.models import Role
        Role.objects.get_or_create(tenant=self.tenant, slug="customer", defaults={"name": "Customer"})

        ensure_customer_profile(self.user)

        assignment = RoleAssignment.objects.filter(tenant=self.tenant, user=self.user, role__slug="customer").first()
        self.assertIsNotNone(assignment)

    def test_ensure_customer_profile_raises_without_person(self):
        orphan = UserAccount.objects.create_user(email="orphan@example.com", tenant=self.tenant)
        with self.assertRaises(ValueError):
            ensure_customer_profile(orphan)


class SeedDemoAccountsTest(TestCase):
    EXPECTED_EMAILS = [
        "owner@salmandyar.local",
        "admin@company.local",
        "nurse.company@salmandyar.local",
        "nurse.independent@salmandyar.local",
        "customer@salmandyar.local",
        "family@salmandyar.local",
    ]

    def test_creates_all_demo_accounts(self):
        call_command("seed_demo_accounts")
        for email in self.EXPECTED_EMAILS:
            self.assertTrue(UserAccount.objects.filter(email=email).exists(), f"missing {email}")

    def test_demo_accounts_have_usable_password(self):
        call_command("seed_demo_accounts")
        for email in self.EXPECTED_EMAILS:
            user = UserAccount.objects.get(email=email)
            self.assertTrue(user.check_password("123456"))

    def test_idempotent(self):
        call_command("seed_demo_accounts")
        call_command("seed_demo_accounts")
        for email in self.EXPECTED_EMAILS:
            self.assertEqual(UserAccount.objects.filter(email=email).count(), 1)

    def test_owner_is_staff_and_superuser(self):
        call_command("seed_demo_accounts")
        owner = UserAccount.objects.get(email="owner@salmandyar.local")
        self.assertTrue(owner.is_staff)
        self.assertTrue(owner.is_superuser)

    def test_independent_caregiver_also_has_customer_profile(self):
        call_command("seed_demo_accounts")
        nurse = UserAccount.objects.get(email="nurse.independent@salmandyar.local")
        self.assertTrue(CaregiverProfile.objects.filter(user=nurse).exists())
        self.assertTrue(CustomerProfile.objects.filter(user=nurse).exists())

    def test_organization_admin_owns_an_organization(self):
        from apps.accounts.models.profiles import OrganizationProfile

        call_command("seed_demo_accounts")
        admin = UserAccount.objects.get(email="admin@company.local")
        self.assertTrue(OrganizationProfile.objects.filter(admin_user=admin).exists())
