"""Every /organization/ page requires an active org-admin membership."""

from .helpers import OrganizationPortalTestCase

PAGES = (
    "/organization/",
    "/organization/staff/",
    "/organization/assignments/",
    "/organization/capacity/",
    "/organization/reports/",
    "/organization/notifications/",
)


class UnauthenticatedAccessTest(OrganizationPortalTestCase):
    def test_every_page_denies_anonymous_users(self):
        for path in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)


class NonAdminAccessTest(OrganizationPortalTestCase):
    def test_authenticated_non_admin_is_denied(self):
        self.client.force_login(self.non_admin_user)
        response = self.client.get("/organization/")
        self.assertEqual(response.status_code, 403)

    def test_staff_member_without_admin_role_is_denied(self):
        self.client.force_login(self.caregiver_user)
        response = self.client.get("/organization/")
        self.assertEqual(response.status_code, 403)


class AuthenticatedAdminAccessTest(OrganizationPortalTestCase):
    def test_every_page_is_reachable_once_logged_in(self):
        self.login_as_admin()
        for path in PAGES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_admin_of_another_organization_cannot_see_this_one(self):
        from apps.accounts.models.profiles import OrganizationMembership, OrganizationProfile, OrgMembershipRole, OrgMembershipStatus

        other_admin = self._create_user(tenant=self.other_tenant, phone="09121110099")
        other_org = OrganizationProfile.objects.create(
            name="Other Co", code="other-co", admin_user=other_admin, tenant=self.other_tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org, user=other_admin, role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )
        self.client.force_login(other_admin)
        response = self.client.get("/organization/")
        self.assertNotContains(response, "Care Co")
