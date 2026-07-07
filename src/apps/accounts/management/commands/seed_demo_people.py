"""
Management command: seed_demo_people
Creates demo records for development. Idempotent.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CompanyAffiliationRequest,
    CustomerProfile,
    ElderProfile,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
    TrustedContact,
)
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount


class Command(BaseCommand):
    help = "Seed demo people for development (idempotent)."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar", defaults={"name": "سالمندیار", "status": "active"},
        )

        # 1. Customer
        cust_user, cust_created = self._get_or_create_user(tenant, "09121111111", "فاطمه رضایی")
        if cust_created:
            CustomerProfile.objects.create(
                user=cust_user, person=cust_user.person, phone="09121111111",
                display_name="فاطمه رضایی", city="tehran", relation_to_elder="child",
            )
            self._assign_role(tenant, cust_user, "customer")

        # 2. Elder profile
        cust_profile = CustomerProfile.objects.filter(user=cust_user).first()
        if cust_profile and not cust_profile.elder_profiles.exists():
            ElderProfile.objects.create(
                customer_profile=cust_profile, full_name="حسن رضایی",
                approximate_age=78, city="tehran", is_primary=True,
            )

        # 3. Trusted contact
        if cust_profile and not cust_profile.trusted_contacts.exists():
            TrustedContact.objects.create(
                customer_profile=cust_profile, full_name="علی رضایی",
                phone="09122222222", relation="brother",
            )

        # 4. Independent caregiver
        cg_user, cg_created = self._get_or_create_user(tenant, "09133333333", "مریم احمدی")
        if cg_created:
            CaregiverProfile.objects.create(
                user=cg_user, person=cg_user.person, phone="09133333333",
                display_name="مریم احمدی", specialty="nurse", city="tehran",
            )
            self._assign_role(tenant, cg_user, "independent_caregiver")

        # 5. Company admin + organization
        admin_user, admin_created = self._get_or_create_user(tenant, "09144444444", "محمد کریمی")
        org = OrganizationProfile.objects.filter(code="DEMO-0001").first()
        if not org:
            org = OrganizationProfile.objects.create(
                name="آژانس مراقبت نور", code="DEMO-0001", admin_user=admin_user,
                company_type="care_agency", city="tehran", phone="09144444444", tenant=tenant,
            )
            OrganizationMembership.objects.get_or_create(
                organization=org, user=admin_user, role_type=OrgMembershipRole.ADMIN,
                defaults={"person": admin_user.person, "status": OrgMembershipStatus.ACTIVE, "joined_at": timezone.now()},
            )
            self._assign_role(tenant, admin_user, "organization_admin")

        # 6. Caregiver with pending affiliation
        aff_user, aff_created = self._get_or_create_user(tenant, "09155555555", "زهرا موسوی")
        if aff_created:
            aff_profile = CaregiverProfile.objects.create(
                user=aff_user, person=aff_user.person, phone="09155555555",
                display_name="زهرا موسوی", specialty="home_caregiver", city="tehran",
            )
            CompanyAffiliationRequest.objects.get_or_create(
                caregiver_profile=aff_profile,
                requested_company_name_or_code="DEMO-0001",
                defaults={"organization": org},
            )
            self._assign_role(tenant, aff_user, "independent_caregiver")

        self.stdout.write(self.style.SUCCESS("Demo people seeded."))

    def _get_or_create_user(self, tenant, phone, name):
        user = UserAccount.objects.filter(phone=phone).first()
        if user:
            return user, False
        person = Person.objects.create(tenant=tenant, full_name=name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return user, True

    def _assign_role(self, tenant, user, slug):
        role = Role.objects.filter(tenant=tenant, slug=slug).first()
        if role:
            RoleAssignment.objects.get_or_create(
                tenant=tenant, user=user, role=role, defaults={"scope_type": "platform"},
            )
