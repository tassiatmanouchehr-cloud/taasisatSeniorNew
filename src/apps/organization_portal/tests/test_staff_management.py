"""Staff list, approve, suspend — Epic 02."""

from apps.accounts.models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus

from .helpers import OrganizationPortalTestCase


class StaffListViewTest(OrganizationPortalTestCase):
    def test_lists_own_staff(self):
        self.login_as_admin()
        response = self.client.get("/organization/staff/")
        self.assertContains(response, "Staff Caregiver")


class StaffApproveViewTest(OrganizationPortalTestCase):
    def test_approve_transitions_pending_to_active(self):
        pending = OrganizationMembership.objects.create(
            organization=self.organization,
            user=self._create_user(tenant=self.tenant, phone="09121110005"),
            role_type=OrgMembershipRole.CAREGIVER,
            status=OrgMembershipStatus.PENDING,
        )
        self.login_as_admin()
        response = self.client.post(f"/organization/staff/{pending.id}/approve/")
        self.assertRedirects(response, "/organization/staff/")

        pending.refresh_from_db()
        self.assertEqual(pending.status, OrgMembershipStatus.ACTIVE)
        self.assertEqual(pending.approved_by_id, self.admin_user.id)
        self.assertIsNotNone(pending.joined_at)

    def test_cannot_approve_another_organizations_staff(self):
        from apps.accounts.models.profiles import OrganizationProfile

        other_org_admin = self._create_user(tenant=self.tenant, phone="09121110007")
        other_org = OrganizationProfile.objects.create(
            name="Other Co",
            code="other-co-2",
            admin_user=other_org_admin,
            tenant=self.tenant,
        )
        other_membership = OrganizationMembership.objects.create(
            organization=other_org,
            user=self._create_user(tenant=self.tenant, phone="09121110006"),
            role_type=OrgMembershipRole.CAREGIVER,
            status=OrgMembershipStatus.PENDING,
        )
        self.login_as_admin()
        response = self.client.post(f"/organization/staff/{other_membership.id}/approve/")
        self.assertEqual(response.status_code, 404)


class StaffSuspendViewTest(OrganizationPortalTestCase):
    def test_suspend_transitions_active_to_suspended(self):
        self.login_as_admin()
        response = self.client.post(f"/organization/staff/{self.staff_membership.id}/suspend/")
        self.assertRedirects(response, "/organization/staff/")

        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, OrgMembershipStatus.SUSPENDED)
