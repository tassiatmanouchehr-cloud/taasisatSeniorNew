"""
Confirmed authorization defect fix — Epic 05 (Permission-Key Registry &
Authorization Hardening).

OrganizationStaffService.approve_membership()/suspend_membership() had
"organization.membership.approve"/"organization.membership.suspend"
permission keys defined and even granted to the organization_admin role
(Epic 04), but no PermissionService.require() call ever enforced them —
the two methods relied entirely on the caller already having passed
resolve_organization()'s upstream ownership check. This is now fixed
directly in both methods, mirroring AssignmentService.assign()'s exact
ownership_authorized_by fallback shape.
"""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.organization_rbac import OrganizationRoleSyncService
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.audit import AuditLog


class OrganizationStaffAuthorizationTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"staffauth-{uuid.uuid4().hex[:8]}", name="Staff Auth Tenant")
        self.admin_user = self._create_user(phone="09140000040")
        self.organization = OrganizationProfile.objects.create(
            name="Care Co", code=f"care-{uuid.uuid4().hex[:8]}", admin_user=self.admin_user, tenant=self.tenant,
        )
        self.admin_membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.admin_user,
            role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )

        self.staff_user = self._create_user(phone="09140000041")
        self.staff_membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.staff_user,
            role_type=OrgMembershipRole.CAREGIVER, status=OrgMembershipStatus.PENDING,
        )

    def _create_user(self, *, phone) -> UserAccount:
        person = Person.objects.create(tenant=self.tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)

    def test_approve_membership_ownership_fallback_still_works(self):
        """No RoleAssignment synced yet — ownership_authorized_by fallback
        keeps this working exactly as before, never a lockout."""
        OrganizationStaffService.approve_membership(self.staff_membership, approved_by=self.admin_user)
        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, OrgMembershipStatus.ACTIVE)

        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id, action="rbac.permission.ownership_authorized",
            ).exists(),
        )

    def test_approve_membership_uses_real_rbac_when_synced(self):
        """Once a real scoped RoleAssignment exists (via sync, exercised
        here through a normal approve of the ADMIN membership itself),
        the real permission check succeeds and no fallback audit fires."""
        OrganizationRoleSyncService.sync_for_membership(self.admin_membership)

        OrganizationStaffService.approve_membership(self.staff_membership, approved_by=self.admin_user)

        self.assertFalse(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id, action="rbac.permission.ownership_authorized",
                resource_id=self.staff_membership.id,
            ).exists(),
        )

    def test_suspend_membership_ownership_fallback_still_works(self):
        OrganizationStaffService.approve_membership(self.staff_membership, approved_by=self.admin_user)
        OrganizationStaffService.suspend_membership(self.staff_membership, suspended_by=self.admin_user)

        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, OrgMembershipStatus.SUSPENDED)

    def test_suspend_membership_with_no_actor_is_true_system_context(self):
        """Backward-compatible: a caller that passes no suspended_by at all
        (matching every pre-Epic-05 call site) still works, audited as
        true system context, not a bypass."""
        OrganizationStaffService.approve_membership(self.staff_membership, approved_by=self.admin_user)
        OrganizationStaffService.suspend_membership(self.staff_membership)

        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, OrgMembershipStatus.SUSPENDED)
        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id, action="rbac.permission.system_context",
            ).exists(),
        )

    def test_wrong_organization_scope_permission_does_not_authorize(self):
        """A real RoleAssignment scoped to a DIFFERENT organization must not
        satisfy this membership's approval check — proves the scope kwarg
        is actually load-bearing, not decorative."""
        other_admin = self._create_user(phone="09140000042")
        other_org = OrganizationProfile.objects.create(
            name="Other Co", code=f"other-{uuid.uuid4().hex[:8]}", admin_user=other_admin, tenant=self.tenant,
        )
        other_membership = OrganizationMembership.objects.create(
            organization=other_org, user=other_admin, role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )
        OrganizationRoleSyncService.sync_for_membership(other_membership)

        # other_admin has a real, active RoleAssignment — but scoped to other_org, not self.organization.
        OrganizationStaffService.approve_membership(self.staff_membership, approved_by=other_admin)

        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id, action="rbac.permission.ownership_authorized",
                actor_id=other_admin.person_id,
            ).exists(),
        )
