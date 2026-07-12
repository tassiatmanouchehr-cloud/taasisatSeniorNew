"""Tests for the seed_product_walkthrough management command."""

import io
from unittest import mock

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
from apps.booking.models import SupplierAssignment
from apps.execution.models import ExecutionSession
from apps.finance.models import FinancialParty, LedgerEntry, PaymentTransaction
from apps.jobs.models import JobDefinition
from apps.kernel.models import RoleAssignment, Tenant, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.kernel.models.event_outbox import EventOutbox
from apps.kernel.models.supplier import ServiceSupplier, SupplierType
from apps.kernel.permissions.keys import (
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_SUSPEND,
)
from apps.kernel.services.permission_service import PermissionService
from apps.orders.models import EligibilityStatus, Order, OrderOrganizationEligibility, OrderStatus
from apps.payments.models import PaymentIntent, PaymentProvider
from apps.wallet.models import Wallet

DEMO_TENANT_SLUG = "demo-senior-platform"
REVOKED_ORDER_MARKER = "PRODUCT_WALKTHROUGH_DEMO:eligible-revoked"
IN_PROGRESS_ORDER_MARKER = "PRODUCT_WALKTHROUGH_DEMO:in-progress"


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


@override_settings(DEBUG=True)
class SeedProductWalkthroughFirstRunCompletenessTest(TestCase):
    """Architecture Review remediation M1: the in-progress example order
    must be genuinely in-progress, with a real ExecutionSession, after
    exactly one run — not requiring a second run to "catch up"."""

    @classmethod
    def setUpTestData(cls):
        _run_command()
        cls.tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        cls.in_progress_order = Order.objects.get(internal_note=IN_PROGRESS_ORDER_MARKER)

    def test_in_progress_order_is_genuinely_in_progress_after_first_run(self):
        self.assertEqual(self.in_progress_order.status, OrderStatus.IN_PROGRESS)

    def test_execution_session_exists_after_first_run(self):
        assignment = SupplierAssignment.objects.filter(order=self.in_progress_order).first()
        self.assertIsNotNone(assignment)
        self.assertTrue(ExecutionSession.objects.filter(supplier_assignment=assignment).exists())

    def test_execution_session_was_started_through_execution_service(self):
        # ExecutionSessionStatus.IN_PROGRESS is only ever reached via
        # ExecutionService.start_session() — a direct model write would
        # default to SCHEDULED. The order reaching Order.status=IN_PROGRESS
        # (asserted above) is itself only possible via start_session()'s
        # internal call to status_machine.start_order(), the sole mutator
        # of that transition — together these prove the real service ran.
        from apps.execution.models import ExecutionSessionStatus

        assignment = SupplierAssignment.objects.filter(order=self.in_progress_order).first()
        session = ExecutionSession.objects.get(supplier_assignment=assignment)
        self.assertEqual(session.status, ExecutionSessionStatus.IN_PROGRESS)


@override_settings(DEBUG=True)
class SeedProductWalkthroughRepeatRunStabilityTest(TestCase):
    """Architecture Review remediation M2/M3 + the related organization
    RoleAssignment sync fix: idempotency means more than "no duplicate
    rows" — a second and third clean run must perform zero unnecessary
    domain mutations, emit zero duplicate audit/event entries, and leave
    every timestamp untouched."""

    @classmethod
    def setUpTestData(cls):
        _run_command()
        cls.tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        cls.after_run1 = cls._snapshot()

        _run_command()
        cls.after_run2 = cls._snapshot()

        _run_command()
        cls.after_run3 = cls._snapshot()

    @classmethod
    def _snapshot(cls):
        return {
            "AuditLog": AuditLog.objects.count(),
            "EventOutbox": EventOutbox.objects.count(),
            "JobDefinition": JobDefinition.objects.count(),
            "FinancialParty": FinancialParty.objects.count(),
            "Wallet": Wallet.objects.count(),
            "PaymentIntent": PaymentIntent.objects.count(),
            "PaymentTransaction": PaymentTransaction.objects.count(),
            "LedgerEntry": LedgerEntry.objects.count(),
            "ExecutionSession": ExecutionSession.objects.count(),
            "RoleAssignment": RoleAssignment.objects.count(),
            "Order": Order.objects.count(),
            "OrderOrganizationEligibility": OrderOrganizationEligibility.objects.count(),
        }

    def test_second_run_does_not_change_audit_log_count(self):
        self.assertEqual(self.after_run1["AuditLog"], self.after_run2["AuditLog"])

    def test_third_run_does_not_change_audit_log_count(self):
        self.assertEqual(self.after_run2["AuditLog"], self.after_run3["AuditLog"])

    def test_second_run_does_not_change_event_outbox_count(self):
        self.assertEqual(self.after_run1["EventOutbox"], self.after_run2["EventOutbox"])

    def test_third_run_does_not_change_event_outbox_count(self):
        self.assertEqual(self.after_run2["EventOutbox"], self.after_run3["EventOutbox"])

    def test_financial_party_and_wallet_counts_remain_stable(self):
        self.assertEqual(self.after_run1["FinancialParty"], self.after_run3["FinancialParty"])
        self.assertEqual(self.after_run1["Wallet"], self.after_run3["Wallet"])

    def test_finance_settlement_rows_remain_stable(self):
        self.assertEqual(self.after_run1["PaymentIntent"], self.after_run3["PaymentIntent"])
        self.assertEqual(self.after_run1["PaymentTransaction"], self.after_run3["PaymentTransaction"])
        self.assertEqual(self.after_run1["LedgerEntry"], self.after_run3["LedgerEntry"])

    def test_no_pending_or_failed_retry_jobs_introduced(self):
        self.assertEqual(JobDefinition.objects.count(), 0)

    def test_execution_session_count_does_not_grow_after_first_run(self):
        self.assertEqual(self.after_run1["ExecutionSession"], self.after_run3["ExecutionSession"])

    def test_dataset_row_counts_are_fully_stable(self):
        self.assertEqual(self.after_run1, self.after_run2)
        self.assertEqual(self.after_run2, self.after_run3)


@override_settings(DEBUG=True)
class SeedProductWalkthroughRevokedEligibilityStabilityTest(TestCase):
    """Architecture Review remediation M2: the revoked-eligibility example
    must reach WITHDRAWN on the first run and never reactivate on any
    subsequent run."""

    @classmethod
    def setUpTestData(cls):
        _run_command()
        cls.tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        cls.order = Order.objects.get(internal_note=REVOKED_ORDER_MARKER)
        cls.org1 = OrganizationProfile.objects.filter(tenant=cls.tenant).order_by("code").first()

    def test_first_run_creates_the_revoked_example_correctly(self):
        eligibility = OrderOrganizationEligibility.objects.get(order=self.order, organization=self.org1)
        self.assertEqual(eligibility.status, EligibilityStatus.WITHDRAWN)

    def test_second_and_third_runs_perform_no_eligibility_transition(self):
        eligibility_before = OrderOrganizationEligibility.objects.get(order=self.order, organization=self.org1)
        status_before = eligibility_before.status
        granted_at_before = eligibility_before.granted_at
        revoked_at_before = eligibility_before.revoked_at

        _run_command()
        _run_command()

        eligibility_after = OrderOrganizationEligibility.objects.get(order=self.order, organization=self.org1)
        self.assertEqual(eligibility_after.status, EligibilityStatus.WITHDRAWN)
        self.assertEqual(eligibility_after.status, status_before)
        self.assertEqual(eligibility_after.granted_at, granted_at_before)
        self.assertEqual(eligibility_after.revoked_at, revoked_at_before)


@override_settings(DEBUG=True)
class SeedProductWalkthroughRouteDiscoveryOutputTest(TestCase):
    """Frontend remediation follow-up (Defect 4): the route-discovery output
    must reflect the provider/organization profile pages added in Epic 06
    Sprint 2, and must stop claiming they don't exist."""

    @classmethod
    def setUpTestData(cls):
        cls.output = _run_command()

    def test_stale_no_profile_page_claim_is_removed(self):
        self.assertNotIn(
            'No customer/provider/organization "profile" page exists as a distinct URL',
            self.output,
        )

    def test_customer_profile_page_absence_still_stated_accurately(self):
        self.assertIn('No customer "profile" page exists as a distinct URL', self.output)

    def test_output_lists_provider_profile_route(self):
        self.assertIn("/provider/profile/", self.output)

    def test_output_lists_provider_profile_edit_route(self):
        self.assertIn("/provider/profile/edit/basic/", self.output)

    def test_output_lists_provider_public_preview_route(self):
        self.assertIn("/find-a-caregiver/", self.output)
        self.assertIn("provider public preview", self.output)

    def test_output_lists_organization_profile_route(self):
        self.assertIn("/organization/profile/", self.output)

    def test_output_lists_organization_profile_edit_route(self):
        self.assertIn("/organization/profile/edit/", self.output)

    def test_output_lists_organization_public_preview_route(self):
        self.assertIn("/find-an-organization/", self.output)
        self.assertIn("organization public preview", self.output)

    def test_printed_preview_urls_carry_the_demo_tenant_hint(self):
        """Frontend remediation R2: the demo dataset lives in its own
        dedicated tenant (not the default tenant public profile views
        resolve against), so every printed preview URL must be directly
        usable as printed — carrying an explicit ?tenant= hint rather than
        requiring the operator to guess or edit the URL."""
        self.assertIn(f"?tenant={DEMO_TENANT_SLUG}", self.output)


@override_settings(DEBUG=True)
class SeedProductWalkthroughReportSideEffectTest(TestCase):
    """Frontend remediation R3: _print_report() must be pure — it must
    never call a write-semantics service merely to produce its output.
    The organization ServiceSupplier this report used to create-on-demand
    (via get_or_create_supplier_for_organization called directly from
    _print_report) is now resolved exactly once, during
    _ensure_organizations (dataset-building), and _print_report only
    reads the already-resolved id."""

    def test_get_or_create_supplier_for_organization_called_exactly_once_per_organization(self):
        from apps.accounts.services.supplier_bridge import (
            get_or_create_supplier_for_organization as real_get_or_create_supplier_for_organization,
        )

        with mock.patch(
            "apps.kernel.management.commands.seed_product_walkthrough.get_or_create_supplier_for_organization",
            wraps=real_get_or_create_supplier_for_organization,
        ) as spy:
            _run_command()

        tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        organization_count = OrganizationProfile.objects.filter(tenant=tenant).count()

        # If _print_report still called this itself, call_count would be
        # organization_count + 1 (once during dataset-building, once again
        # while printing the report for organizations[0]).
        self.assertEqual(spy.call_count, organization_count)

    def test_second_run_calls_supplier_resolution_zero_times_report_included(self):
        """On a second (idempotent) run, get_or_create_supplier_for_organization
        should not be called at all from reporting — proving the reporting
        phase performs no write-semantics calls even indirectly."""
        _run_command()

        from apps.accounts.services.supplier_bridge import (
            get_or_create_supplier_for_organization as real_get_or_create_supplier_for_organization,
        )

        with mock.patch(
            "apps.kernel.management.commands.seed_product_walkthrough.get_or_create_supplier_for_organization",
            wraps=real_get_or_create_supplier_for_organization,
        ) as spy:
            _run_command()

        tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        organization_count = OrganizationProfile.objects.filter(tenant=tenant).count()

        # get_or_create_supplier_for_organization is still called once per
        # organization during _ensure_organizations (it is a get_or_create,
        # so this is a no-op lookup, not a write) — but never an additional
        # time from _print_report.
        self.assertEqual(spy.call_count, organization_count)

    def test_reporting_does_not_change_service_supplier_count(self):
        output_first = _run_command()
        tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        supplier_count_after_first_report = ServiceSupplier.objects.filter(tenant=tenant).count()

        output_second = _run_command()
        supplier_count_after_second_report = ServiceSupplier.objects.filter(tenant=tenant).count()

        self.assertEqual(supplier_count_after_first_report, supplier_count_after_second_report)
        self.assertIn(f"?tenant={DEMO_TENANT_SLUG}", output_first)
        self.assertIn(f"?tenant={DEMO_TENANT_SLUG}", output_second)

    def test_reporting_emits_no_audit_or_event_outbox_rows(self):
        _run_command()
        audit_count_after_first = AuditLog.objects.count()
        event_count_after_first = EventOutbox.objects.count()

        _run_command()
        audit_count_after_second = AuditLog.objects.count()
        event_count_after_second = EventOutbox.objects.count()

        self.assertEqual(audit_count_after_first, audit_count_after_second)
        self.assertEqual(event_count_after_first, event_count_after_second)

    def test_repeated_execution_remains_stable_for_organization_suppliers(self):
        """First run creates every organization supplier; every subsequent
        resolution of the same organization must return the identical
        supplier row (same id), never a new one — a clean repeat run's
        'created=0 updated=0' expectation, isolated to the org-supplier
        resolution site."""
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization

        _run_command()
        tenant = Tenant.objects.get(slug=DEMO_TENANT_SLUG)
        organizations = list(OrganizationProfile.objects.filter(tenant=tenant))
        supplier_ids_before = {
            org.pk: get_or_create_supplier_for_organization(org, tenant_id=tenant.id).id for org in organizations
        }

        supplier_ids_after = {
            org.pk: get_or_create_supplier_for_organization(org, tenant_id=tenant.id).id for org in organizations
        }

        self.assertEqual(supplier_ids_before, supplier_ids_after)
