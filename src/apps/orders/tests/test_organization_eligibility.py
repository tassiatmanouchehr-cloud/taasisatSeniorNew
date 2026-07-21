"""OrderEligibilityService and OrderOrganizationEligibility — Epic 04
(Enterprise Organization Isolation)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import OrganizationProfile, ProfileStatus
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.orders.models import (
    CatalogStatus,
    EligibilityStatus,
    Order,
    OrderOrganizationEligibility,
    OrderSource,
    OrderStatus,
    ServiceCategory,
)
from apps.orders.services.eligibility_service import OrderEligibilityError, OrderEligibilityService


class EligibilityTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"elig-{uuid.uuid4().hex[:8]}", name="Eligibility Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"elig-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            description="Need home care",
            city="tehran",
            address="Some address",
            phone="09120000000",
        )
        self.admin_user = self._create_user(tenant=self.tenant, phone="09121110001")
        self.organization = OrganizationProfile.objects.create(
            name="Care Co",
            code=f"care-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=self.tenant,
        )
        self.other_organization = OrganizationProfile.objects.create(
            name="Other Co",
            code=f"other-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=self.tenant,
        )

    def _create_user(self, *, tenant, phone) -> UserAccount:
        person = Person.objects.create(tenant=tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)


class GrantRevokeReactivateTest(EligibilityTestCase):
    def test_grant_creates_active_row(self):
        eligibility = OrderEligibilityService.grant(
            order=self.order,
            organization=self.organization,
            granted_by=self.admin_user,
        )
        self.assertEqual(eligibility.status, EligibilityStatus.ACTIVE)
        self.assertEqual(eligibility.tenant_id, self.tenant.id)
        self.assertEqual(eligibility.source, "manual")
        self.assertEqual(eligibility.granted_by_id, self.admin_user.id)

    def test_duplicate_grant_is_idempotent_no_duplicate_row(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        self.assertEqual(
            OrderOrganizationEligibility.objects.filter(order=self.order, organization=self.organization).count(),
            1,
        )

    def test_revoke_sets_withdrawn(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        eligibility = OrderEligibilityService.revoke(
            order=self.order,
            organization=self.organization,
            revoked_by=self.admin_user,
        )
        self.assertEqual(eligibility.status, EligibilityStatus.WITHDRAWN)
        self.assertEqual(eligibility.revoked_by_id, self.admin_user.id)
        self.assertIsNotNone(eligibility.revoked_at)

    def test_duplicate_revoke_is_safe_noop(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        OrderEligibilityService.revoke(order=self.order, organization=self.organization)
        eligibility = OrderEligibilityService.revoke(order=self.order, organization=self.organization)
        self.assertEqual(eligibility.status, EligibilityStatus.WITHDRAWN)

    def test_revoke_nonexistent_pair_returns_none(self):
        result = OrderEligibilityService.revoke(order=self.order, organization=self.organization)
        self.assertIsNone(result)

    def test_reactivate_withdrawn_row_in_place_no_duplicate(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        OrderEligibilityService.revoke(order=self.order, organization=self.organization)
        eligibility = OrderEligibilityService.reactivate(order=self.order, organization=self.organization)

        self.assertEqual(eligibility.status, EligibilityStatus.ACTIVE)
        self.assertIsNone(eligibility.revoked_at)
        self.assertEqual(
            OrderOrganizationEligibility.objects.filter(order=self.order, organization=self.organization).count(),
            1,
        )

    def test_reactivate_already_active_is_noop(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        eligibility = OrderEligibilityService.reactivate(order=self.order, organization=self.organization)
        self.assertEqual(eligibility.status, EligibilityStatus.ACTIVE)

    def test_grant_after_withdrawal_reactivates_rather_than_duplicating(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        OrderEligibilityService.revoke(order=self.order, organization=self.organization)
        eligibility = OrderEligibilityService.grant(order=self.order, organization=self.organization)

        self.assertEqual(eligibility.status, EligibilityStatus.ACTIVE)
        self.assertEqual(
            OrderOrganizationEligibility.objects.filter(order=self.order, organization=self.organization).count(),
            1,
        )

    def test_multiple_organizations_can_be_eligible_for_one_order(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        OrderEligibilityService.grant(order=self.order, organization=self.other_organization)
        self.assertEqual(
            OrderEligibilityService.list_active_for_order(self.order).count(),
            2,
        )

    def test_zero_eligible_organizations_by_default(self):
        self.assertEqual(OrderEligibilityService.list_active_for_order(self.order).count(), 0)
        self.assertFalse(OrderEligibilityService.is_eligible(order=self.order, organization=self.organization))


class TenantConsistencyTest(EligibilityTestCase):
    def test_tenant_mismatch_between_order_and_organization_rejected(self):
        cross_tenant_org = OrganizationProfile.objects.create(
            name="Cross Co",
            code=f"cross-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=self.other_tenant,
        )
        with self.assertRaises(OrderEligibilityError):
            OrderEligibilityService.grant(order=self.order, organization=cross_tenant_org)

    def test_null_tenant_organization_rejected(self):
        null_tenant_org = OrganizationProfile.objects.create(
            name="Null Tenant Co",
            code=f"null-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=None,
        )
        with self.assertRaises(OrderEligibilityError):
            OrderEligibilityService.grant(order=self.order, organization=null_tenant_org)


class SuspendedOrganizationTest(EligibilityTestCase):
    def test_is_eligible_false_when_organization_suspended(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        self.organization.status = ProfileStatus.SUSPENDED
        self.organization.save(update_fields=["status"])

        self.assertFalse(OrderEligibilityService.is_eligible(order=self.order, organization=self.organization))


class AuditAndEventTest(EligibilityTestCase):
    def test_grant_publishes_audited_domain_event(self):
        with self.captureOnCommitCallbacks(execute=True):
            OrderEligibilityService.grant(order=self.order, organization=self.organization, granted_by=self.admin_user)

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="domain_event.OrderEligibilityGranted").exists(),
        )

    def test_revoke_publishes_audited_domain_event(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        with self.captureOnCommitCallbacks(execute=True):
            OrderEligibilityService.revoke(order=self.order, organization=self.organization, revoked_by=self.admin_user)

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="domain_event.OrderEligibilityRevoked").exists(),
        )


class ModelConstraintTest(EligibilityTestCase):
    def test_unique_together_order_organization(self):
        OrderOrganizationEligibility.objects.create(
            tenant_id=self.tenant.id,
            order=self.order,
            organization=self.organization,
        )
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderOrganizationEligibility.objects.create(
                tenant_id=self.tenant.id,
                order=self.order,
                organization=self.organization,
            )

    def test_for_tenant_scopes_eligibility_rows(self):
        OrderEligibilityService.grant(order=self.order, organization=self.organization)
        self.assertEqual(OrderOrganizationEligibility.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(OrderOrganizationEligibility.objects.for_tenant(self.other_tenant.id).count(), 0)
