"""OrganizationRoleSyncService — Epic 04 (Enterprise Organization Isolation)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.organization_rbac import (
    ORGANIZATION_ADMIN_ROLE_SLUG,
    OrganizationRoleSyncError,
    OrganizationRoleSyncService,
)
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount
from apps.kernel.services.permission_service import PermissionService


class OrganizationRbacTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"rbac-{uuid.uuid4().hex[:8]}", name="RBAC Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"rbac-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.admin_user = self._create_user(tenant=self.tenant, phone="09121140001")
        self.organization = OrganizationProfile.objects.create(
            name="Care Co",
            code=f"care-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=self.tenant,
        )

    def _create_user(self, *, tenant, phone) -> UserAccount:
        person = Person.objects.create(tenant=tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)

    def _create_membership(self, *, role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE, user=None):
        user = user or self.admin_user
        return OrganizationMembership.objects.create(
            organization=self.organization,
            user=user,
            role_type=role_type,
            status=status,
        )


class SyncBasicsTest(OrganizationRbacTestCase):
    def test_active_admin_membership_creates_active_role_assignment(self):
        membership = self._create_membership()
        assignment = OrganizationRoleSyncService.sync_for_membership(membership)

        self.assertIsNotNone(assignment)
        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.scope_type, "organization")
        self.assertEqual(assignment.scope_id, self.organization.id)
        self.assertEqual(assignment.role.slug, ORGANIZATION_ADMIN_ROLE_SLUG)

    def test_non_admin_role_type_is_not_synced(self):
        membership = self._create_membership(role_type=OrgMembershipRole.CAREGIVER)
        result = OrganizationRoleSyncService.sync_for_membership(membership)
        self.assertIsNone(result)
        self.assertFalse(RoleAssignment.objects.filter(user=self.admin_user, scope_type="organization").exists())

    def test_repeated_sync_is_idempotent_no_duplicate_row(self):
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)
        OrganizationRoleSyncService.sync_for_membership(membership)

        self.assertEqual(
            RoleAssignment.objects.filter(
                user=self.admin_user,
                scope_type="organization",
                scope_id=self.organization.id,
            ).count(),
            1,
        )

    def test_suspended_membership_deactivates_role_assignment(self):
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)

        membership.status = OrgMembershipStatus.SUSPENDED
        membership.save(update_fields=["status"])
        assignment = OrganizationRoleSyncService.sync_for_membership(membership)

        self.assertFalse(assignment.is_active)

    def test_role_is_created_idempotently_with_permissions(self):
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)

        role = Role.objects.get(tenant=self.tenant, slug=ORGANIZATION_ADMIN_ROLE_SLUG)
        self.assertIn("booking.assignment.assign", role.permissions)
        self.assertIn("organization.membership.approve", role.permissions)
        self.assertIn("organization.membership.suspend", role.permissions)

    def test_second_organization_gets_independent_scoped_assignment(self):
        other_org = OrganizationProfile.objects.create(
            name="Other Co",
            code=f"other-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=self.tenant,
        )
        membership_a = self._create_membership()
        other_membership = OrganizationMembership.objects.create(
            organization=other_org,
            user=self.admin_user,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        OrganizationRoleSyncService.sync_for_membership(membership_a)
        OrganizationRoleSyncService.sync_for_membership(other_membership)

        self.assertEqual(
            RoleAssignment.objects.filter(user=self.admin_user, scope_type="organization", is_active=True).count(),
            2,
        )


class TenantConsistencyTest(OrganizationRbacTestCase):
    def test_organization_tenant_mismatch_with_user_rejected(self):
        cross_tenant_org = OrganizationProfile.objects.create(
            name="Cross Co",
            code=f"cross-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=self.other_tenant,
        )
        membership = OrganizationMembership.objects.create(
            organization=cross_tenant_org,
            user=self.admin_user,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        with self.assertRaises(OrganizationRoleSyncError):
            OrganizationRoleSyncService.sync_for_membership(membership)

    def test_null_tenant_organization_rejected(self):
        null_org = OrganizationProfile.objects.create(
            name="Null Co",
            code=f"null-{uuid.uuid4().hex[:8]}",
            admin_user=self.admin_user,
            tenant=None,
        )
        membership = OrganizationMembership.objects.create(
            organization=null_org,
            user=self.admin_user,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        with self.assertRaises(OrganizationRoleSyncError):
            OrganizationRoleSyncService.sync_for_membership(membership)


class ScopedPermissionEvaluationTest(OrganizationRbacTestCase):
    """Proves the activated RoleAssignment is actually consulted by
    PermissionService — not just created and ignored."""

    def test_scoped_permission_check_succeeds_for_own_organization(self):
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)

        self.assertTrue(
            PermissionService.check(
                self.admin_user,
                "booking.assignment.assign",
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": str(self.organization.id)},
            ),
        )

    def test_scoped_permission_check_fails_for_a_different_organization(self):
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)

        other_org_id = uuid.uuid4()
        self.assertFalse(
            PermissionService.check(
                self.admin_user,
                "booking.assignment.assign",
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": str(other_org_id)},
            ),
        )

    def test_unscoped_check_no_longer_matches_an_organization_scoped_assignment(self):
        """Epic 05 (Permission-Key Registry & Authorization Hardening)
        scope validation hardening: an organization-scoped RoleAssignment
        must NOT satisfy an unscoped (platform-wide) permission check —
        fixed in apps.kernel.services.permission_service.PermissionService
        ._scope_matches(). Before this fix, `scope is None` short-circuited
        `True` for any assignment regardless of its own scope_type; this
        test documented that gap in Epic 04 and now documents the fix."""
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)

        self.assertFalse(
            PermissionService.check(self.admin_user, "booking.assignment.assign", tenant_id=self.tenant.id),
        )

    def test_deactivated_assignment_no_longer_authorizes(self):
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)

        membership.status = OrgMembershipStatus.SUSPENDED
        membership.save(update_fields=["status"])
        OrganizationRoleSyncService.sync_for_membership(membership)

        self.assertFalse(
            PermissionService.check(
                self.admin_user,
                "booking.assignment.assign",
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": str(self.organization.id)},
            ),
        )


class CrossTenantRbacTest(OrganizationRbacTestCase):
    def test_role_assignment_from_one_tenant_does_not_leak_to_another(self):
        membership = self._create_membership()
        OrganizationRoleSyncService.sync_for_membership(membership)

        self.assertFalse(
            PermissionService.check(
                self.admin_user,
                "booking.assignment.assign",
                tenant_id=self.other_tenant.id,
                scope={"scope_type": "organization", "scope_id": str(self.organization.id)},
            ),
        )
