"""backfill_organization_role_assignments — Epic 04 (Enterprise Organization Isolation)."""

import uuid

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.kernel.models import Person, RoleAssignment, Tenant, UserAccount


class BackfillOrganizationRoleAssignmentsTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"backfill-{uuid.uuid4().hex[:8]}", name="Backfill Tenant")
        self.admin_user = self._create_user(phone="09121150001")
        self.organization = OrganizationProfile.objects.create(
            name="Care Co", code=f"care-{uuid.uuid4().hex[:8]}", admin_user=self.admin_user, tenant=self.tenant,
        )
        self.membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.admin_user,
            role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )

        self.caregiver_user = self._create_user(phone="09121150002")
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.caregiver_user,
            role_type=OrgMembershipRole.CAREGIVER, status=OrgMembershipStatus.ACTIVE,
        )

    def _create_user(self, *, phone) -> UserAccount:
        person = Person.objects.create(tenant=self.tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)

    def test_backfill_creates_role_assignment_for_active_admin(self):
        call_command("backfill_organization_role_assignments")
        self.assertTrue(
            RoleAssignment.objects.filter(
                user=self.admin_user, scope_type="organization", scope_id=self.organization.id, is_active=True,
            ).exists(),
        )

    def test_backfill_does_not_sync_non_admin_role_types(self):
        call_command("backfill_organization_role_assignments")
        self.assertFalse(RoleAssignment.objects.filter(user=self.caregiver_user, scope_type="organization").exists())

    def test_backfill_is_idempotent(self):
        call_command("backfill_organization_role_assignments")
        call_command("backfill_organization_role_assignments")
        self.assertEqual(
            RoleAssignment.objects.filter(user=self.admin_user, scope_type="organization").count(), 1,
        )

    def test_dry_run_writes_nothing(self):
        call_command("backfill_organization_role_assignments", "--dry-run")
        self.assertFalse(RoleAssignment.objects.filter(user=self.admin_user, scope_type="organization").exists())

    def test_skips_membership_with_null_tenant_organization_without_crashing(self):
        null_org = OrganizationProfile.objects.create(
            name="Null Co", code=f"null-{uuid.uuid4().hex[:8]}", admin_user=self.admin_user, tenant=None,
        )
        broken_user = self._create_user(phone="09121150003")
        OrganizationMembership.objects.create(
            organization=null_org, user=broken_user, role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )

        call_command("backfill_organization_role_assignments")

        self.assertTrue(
            RoleAssignment.objects.filter(user=self.admin_user, scope_type="organization").exists(),
        )
        self.assertFalse(RoleAssignment.objects.filter(user=broken_user, scope_type="organization").exists())
