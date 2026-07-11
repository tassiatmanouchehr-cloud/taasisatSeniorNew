"""Tests for the seed_product_walkthrough management command."""

import io

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CaregiverProviderType,
    CustomerProfile,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.kernel.models import RoleAssignment, Tenant, UserAccount
from apps.kernel.models.supplier import ServiceSupplier, SupplierType
from apps.kernel.permissions.keys import (
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_SUSPEND,
)
from apps.kernel.services.permission_service import PermissionService
from apps.orders.models import EligibilityStatus, Order, OrderOrganizationEligibility
from apps.payments.models import PaymentIntent, PaymentProvider

DEMO_TENANT_SLUG = "demo-senior-platform"


def _run_command():
    out = io.StringIO()
    call_command("seed_product_walkthrough", stdout=out)
    return out.getvalue()


class SeedProductWalkthroughDebugGuardTest(TestCase):
    """DEBUG=False must refuse to run — this class deliberately does NOT
    override DEBUG, so it inherits the real testing-settings value (False)."""

    def test_refuses_when_debug_false(self):
        with self.assertRaises(CommandError):
            call_command("seed_product_walkthrough")

        self.assertFalse(Tenant.objects.filter(slug=DEMO_TENANT_SLUG).exists())


@override_settings(DEBUG=True)
class SeedProductWalkthroughDatasetTest(TestCase):
    """One command invocation, many independent assertions against the
    resulting state — avoids re-running the (deliberately large) seed
    command once per assertion."""

    @classmethod
    def setUpTestData(cls):
        _run_command()
        cls.tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)

    def test_first_run_succeeds_with_expected_tenant(self):
        self.assertEqual(self.tenant.status, "active")

    def test_customer_profiles_created(self):
        customers = CustomerProfile.objects.filter(user__tenant=self.tenant)
        self.assertEqual(customers.count(), 3)

        primary = CustomerProfile.objects.get(user__email="demo.customer@example.test")
        active_recipients = primary.elder_profiles.exclude(status="archived")
        archived_recipients = primary.elder_profiles.filter(status="archived")
        self.assertEqual(active_recipients.count(), 1)
        self.assertEqual(archived_recipients.count(), 1)

    def test_independent_providers_created_correctly(self):
        independents = CaregiverProfile.objects.filter(
            user__tenant=self.tenant,
            provider_type=CaregiverProviderType.INDEPENDENT,
        )
        self.assertEqual(independents.count(), 5)
        for profile in independents:
            supplier = ServiceSupplier.objects.get(
                linked_entity_type="CaregiverProfile",
                linked_entity_id=profile.id,
            )
            self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)
            self.assertEqual(supplier.tenant_id, self.tenant.id)

    def test_organization_profiles_created(self):
        orgs = OrganizationProfile.objects.filter(tenant=self.tenant)
        self.assertEqual(orgs.count(), 2)
        for org in orgs:
            self.assertEqual(org.status, "active")
            admin_membership = OrganizationMembership.objects.get(
                organization=org,
                role_type=OrgMembershipRole.ADMIN,
            )
            self.assertEqual(admin_membership.status, OrgMembershipStatus.ACTIVE)

    def test_organization_admins_receive_scoped_rbac(self):
        orgs = OrganizationProfile.objects.filter(tenant=self.tenant)
        for org in orgs:
            admin_membership = OrganizationMembership.objects.get(
                organization=org,
                role_type=OrgMembershipRole.ADMIN,
            )
            scoped_assignment = RoleAssignment.objects.filter(
                tenant=self.tenant,
                user=admin_membership.user,
                scope_type="organization",
                scope_id=org.id,
                is_active=True,
            )
            self.assertTrue(scoped_assignment.exists(), f"missing organization-scoped RoleAssignment for {org.name}")

            scope = {"scope_type": "organization", "scope_id": str(org.id)}
            self.assertTrue(
                PermissionService.check(
                    admin_membership.user,
                    ORGANIZATION_MEMBERSHIP_APPROVE,
                    tenant_id=self.tenant.id,
                    scope=scope,
                )
            )
            self.assertTrue(
                PermissionService.check(
                    admin_membership.user,
                    ORGANIZATION_MEMBERSHIP_SUSPEND,
                    tenant_id=self.tenant.id,
                    scope=scope,
                )
            )

    def test_affiliated_providers_have_organization_provider_suppliers(self):
        affiliated = CaregiverProfile.objects.filter(
            user__tenant=self.tenant,
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
        )
        self.assertEqual(affiliated.count(), 6)
        for profile in affiliated:
            supplier = ServiceSupplier.objects.get(
                linked_entity_type="CaregiverProfile",
                linked_entity_id=profile.id,
            )
            self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION_PROVIDER)

    def test_tenant_isolation_intact(self):
        # Everything the command created must resolve to the demo tenant —
        # no leakage into any other tenant (e.g. the real default "salmandyar"
        # tenant used by other seed commands).
        for user in UserAccount.objects.filter(email__endswith="@example.test"):
            self.assertEqual(user.tenant_id, self.tenant.id)
        for order in Order.objects.filter(internal_note__startswith="PRODUCT_WALKTHROUGH_DEMO"):
            self.assertEqual(order.tenant_id, self.tenant.id)

    def test_explicit_eligibility_created_through_service(self):
        org1, org2 = OrganizationProfile.objects.filter(tenant=self.tenant).order_by("code")

        only_org1 = Order.objects.get(internal_note="PRODUCT_WALKTHROUGH_DEMO:eligible-org1-only")
        only_org2 = Order.objects.get(internal_note="PRODUCT_WALKTHROUGH_DEMO:eligible-org2-only")
        both = Order.objects.get(internal_note="PRODUCT_WALKTHROUGH_DEMO:eligible-both")
        none = Order.objects.get(internal_note="PRODUCT_WALKTHROUGH_DEMO:eligible-none")
        revoked = Order.objects.get(internal_note="PRODUCT_WALKTHROUGH_DEMO:eligible-revoked")

        self.assertTrue(
            OrderOrganizationEligibility.objects.filter(
                order=only_org1, organization=org1, status=EligibilityStatus.ACTIVE
            ).exists()
        )
        self.assertFalse(
            OrderOrganizationEligibility.objects.filter(
                order=only_org1, organization=org2, status=EligibilityStatus.ACTIVE
            ).exists()
        )

        self.assertTrue(
            OrderOrganizationEligibility.objects.filter(
                order=only_org2, organization=org2, status=EligibilityStatus.ACTIVE
            ).exists()
        )
        self.assertFalse(
            OrderOrganizationEligibility.objects.filter(
                order=only_org2, organization=org1, status=EligibilityStatus.ACTIVE
            ).exists()
        )

        self.assertTrue(
            OrderOrganizationEligibility.objects.filter(
                order=both, organization=org1, status=EligibilityStatus.ACTIVE
            ).exists()
        )
        self.assertTrue(
            OrderOrganizationEligibility.objects.filter(
                order=both, organization=org2, status=EligibilityStatus.ACTIVE
            ).exists()
        )

        self.assertFalse(OrderOrganizationEligibility.objects.filter(order=none).exists())

        self.assertTrue(
            OrderOrganizationEligibility.objects.filter(
                order=revoked, organization=org1, status=EligibilityStatus.WITHDRAWN
            ).exists()
        )
        self.assertFalse(
            OrderOrganizationEligibility.objects.filter(
                order=revoked, organization=org1, status=EligibilityStatus.ACTIVE
            ).exists()
        )

    def test_suspended_membership_policy_correct(self):
        suspended = OrganizationMembership.objects.filter(
            organization__tenant=self.tenant,
            status=OrgMembershipStatus.SUSPENDED,
        )
        self.assertEqual(suspended.count(), 1)
        membership = suspended.first()
        self.assertEqual(membership.role_type, OrgMembershipRole.CAREGIVER)

        # Suspension is a membership-status change only — the caregiver
        # remains ORGANIZATION_AFFILIATED throughout, per the approved
        # architecture (provider_type is never toggled by suspension).
        profile = CaregiverProfile.objects.get(user=membership.user)
        self.assertEqual(profile.provider_type, CaregiverProviderType.ORGANIZATION_AFFILIATED)

    def test_no_external_provider_called(self):
        intents = PaymentIntent.objects.filter(tenant=self.tenant)
        self.assertTrue(intents.exists())
        for intent in intents:
            self.assertEqual(intent.provider, PaymentProvider.FAKE)


@override_settings(DEBUG=True)
class SeedProductWalkthroughIdempotencyTest(TestCase):
    def test_second_run_is_idempotent_no_duplicate_rows(self):
        _run_command()
        tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)

        counts_after_first = self._snapshot(tenant)

        _run_command()
        counts_after_second = self._snapshot(tenant)

        self.assertEqual(counts_after_first, counts_after_second)

    def _snapshot(self, tenant):
        return {
            "users": UserAccount.objects.filter(tenant=tenant).count(),
            "customer_profiles": CustomerProfile.objects.filter(user__tenant=tenant).count(),
            "caregiver_profiles": CaregiverProfile.objects.filter(user__tenant=tenant).count(),
            "organizations": OrganizationProfile.objects.filter(tenant=tenant).count(),
            "memberships": OrganizationMembership.objects.filter(organization__tenant=tenant).count(),
            "suppliers": ServiceSupplier.objects.filter(tenant=tenant).count(),
            "role_assignments": RoleAssignment.objects.filter(tenant=tenant).count(),
            "orders": Order.objects.filter(tenant=tenant).count(),
            "eligibility": OrderOrganizationEligibility.objects.filter(tenant=tenant).count(),
        }


@override_settings(DEBUG=True)
class SeedProductWalkthroughResetDemoTest(TestCase):
    def test_reset_demo_affects_only_demo_records(self):
        _run_command()

        other_tenant = Tenant.objects.create(slug="other-real-tenant", name="Other Tenant", status="active")
        from apps.kernel.models import Person

        person = Person.objects.create(tenant=other_tenant, full_name="Real Person Not Demo")
        real_user = UserAccount.objects.create_user(
            email="real.person@notdemo.example",
            phone="09099999999",
            person=person,
            tenant=other_tenant,
            password="irrelevant",
        )

        call_command("seed_product_walkthrough", "--reset-demo")

        self.assertTrue(Tenant.objects.filter(slug="other-real-tenant").exists())
        self.assertTrue(UserAccount.objects.filter(pk=real_user.pk).exists())

        # Demo tenant itself is kept (stable identity) and its content rebuilt.
        demo_tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        self.assertEqual(CustomerProfile.objects.filter(user__tenant=demo_tenant).count(), 3)
