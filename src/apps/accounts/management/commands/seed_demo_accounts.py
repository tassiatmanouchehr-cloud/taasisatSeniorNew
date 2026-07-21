"""
Management command: seed_demo_accounts

Creates predictable, email+password-login demo accounts for local
development — distinct from seed_demo_people (phone/OTP-only, no usable
password). Idempotent: running twice does not duplicate data.

Also demonstrates the Module 21A multi-role identity fix directly: the
independent caregiver demo account additionally gets a CustomerProfile
attached to the *same* UserAccount (via ensure_customer_profile), matching
the module's own example — "a caregiver should be able to use the same
account as a customer when searching for a physiotherapist."

Development only.

Usage:
    python manage.py seed_demo_accounts
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CaregiverProviderType,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.profiles import ensure_caregiver_profile, ensure_customer_profile
from apps.accounts.services.registration import assign_role
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
from apps.kernel.models import Person, UserAccount
from apps.kernel.services.tenant_service import TenantService

DEMO_PASSWORD = "123456"

ORG_CODE = "DEMO-COMPANY"
ORG_NAME = "شرکت مراقبت نمونه"


class Command(BaseCommand):
    help = "Seed predictable demo accounts with email/password login (development only, idempotent)."

    def handle(self, *args, **options):
        tenant = TenantService.get_default_tenant()
        call_command("seed_auth_roles")  # ensure the role slugs we assign below exist

        owner = self._get_or_create_user(
            tenant, "owner@salmandyar.local", "مالک پلتفرم", is_staff=True, is_superuser=True
        )
        assign_role(tenant=tenant, user=owner, role_slug="platform_owner")

        org_admin = self._get_or_create_user(tenant, "admin@company.local", "مدیر سازمان نمونه")
        organization = self._ensure_organization(tenant, org_admin)
        assign_role(tenant=tenant, user=org_admin, role_slug="organization_admin")

        org_nurse = self._get_or_create_user(tenant, "nurse.company@salmandyar.local", "پرستار سازمانی")
        self._ensure_org_caregiver_profile(org_nurse, organization)
        assign_role(tenant=tenant, user=org_nurse, role_slug="organization_caregiver")

        independent_nurse = self._get_or_create_user(tenant, "nurse.independent@salmandyar.local", "پرستار مستقل")
        ensure_caregiver_profile(independent_nurse, provider_type=CaregiverProviderType.INDEPENDENT)
        # Multi-role demonstration: the same account can also act as a customer.
        ensure_customer_profile(independent_nurse)

        customer = self._get_or_create_user(tenant, "customer@salmandyar.local", "مشتری نمونه")
        ensure_customer_profile(customer)

        family = self._get_or_create_user(tenant, "family@salmandyar.local", "عضو خانواده نمونه")
        ensure_customer_profile(family, relation_to_elder="family_member", is_primary_family_contact=False)

        self.stdout.write(self.style.SUCCESS("Demo accounts seeded (password for all: 123456):"))
        for email, role in [
            ("owner@salmandyar.local", "Platform Owner"),
            ("admin@company.local", "Organization Admin"),
            ("nurse.company@salmandyar.local", "Organization Caregiver"),
            ("nurse.independent@salmandyar.local", "Independent Caregiver (+ Customer)"),
            ("customer@salmandyar.local", "Customer"),
            ("family@salmandyar.local", "Family Member"),
        ]:
            self.stdout.write(f"  {email}  ({role})")

    def _get_or_create_user(self, tenant, email, full_name, **extra_fields):
        user = UserAccount.objects.filter(email=email).first()
        if user:
            return user
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(email=email, person=person, tenant=tenant, **extra_fields)
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _ensure_organization(self, tenant, admin_user) -> OrganizationProfile:
        org, created = OrganizationProfile.objects.get_or_create(
            code=ORG_CODE,
            defaults={"name": ORG_NAME, "admin_user": admin_user, "tenant": tenant, "company_type": "care_agency"},
        )
        if created:
            OrganizationMembership.objects.get_or_create(
                organization=org,
                user=admin_user,
                role_type=OrgMembershipRole.ADMIN,
                defaults={"person": admin_user.person, "status": OrgMembershipStatus.ACTIVE},
            )
        # Core Profile-ServiceSupplier Invariant Remediation, Phase 9: this
        # organization is created ACTIVE (the model default) directly, not
        # through ProfileActivationService — a direct ACTIVE write must not
        # bypass supplier synchronization. Sanctioned-bridge call only,
        # idempotent, mirrors seed_product_walkthrough.py's own pattern.
        get_or_create_supplier_for_organization(org, tenant_id=tenant.id)
        return org

    def _ensure_org_caregiver_profile(self, user, organization) -> CaregiverProfile:
        profile = ensure_caregiver_profile(
            user,
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
        )
        OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            role_type=OrgMembershipRole.CAREGIVER,
            defaults={"person": user.person, "status": OrgMembershipStatus.ACTIVE},
        )
        return profile
