"""Phase 3 Sprint 3.1 — provider_portal's own "company" affiliation
self-service page (join by code, respond to invitations, leave)."""

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CaregiverProviderType,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
    ProfileStatus,
)
from apps.accounts.services import affiliations as affiliation_services
from apps.kernel.models import Person, UserAccount

from .helpers import ProviderPortalTestCase


class _CompanyFixtureMixin:
    _next_admin_phone = 9129990010

    def _make_organization(self, *, code="join-test-co", name="Join Test Co"):
        type(self)._next_admin_phone += 1
        admin_person = Person.objects.create(tenant=self.tenant, full_name="Org Admin")
        admin_user = UserAccount.objects.create_user(
            phone=f"0{type(self)._next_admin_phone}",
            person=admin_person,
            tenant=self.tenant,
        )
        organization = OrganizationProfile.objects.create(
            name=name,
            code=code,
            admin_user=admin_user,
            tenant=self.tenant,
            status=ProfileStatus.ACTIVE,
        )
        OrganizationMembership.objects.create(
            organization=organization,
            user=admin_user,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        return organization, admin_user


class CompanyJoinViewTest(_CompanyFixtureMixin, ProviderPortalTestCase):
    def test_submit_valid_code_creates_pending_request(self):
        organization, _ = self._make_organization()
        self.login_as_provider()
        response = self.client.post("/provider/company/join/", {"code": organization.code})
        self.assertRedirects(response, "/provider/company/")

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        requests = affiliation_services.list_affiliation_requests_for_caregiver(caregiver)
        self.assertEqual(requests[0].organization, organization)

    def test_invalid_code_creates_no_request(self):
        self.login_as_provider()
        response = self.client.post("/provider/company/join/", {"code": "no-such-code"})
        self.assertRedirects(response, "/provider/company/")

        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(list(affiliation_services.list_affiliation_requests_for_caregiver(caregiver)), [])

    def test_company_page_shows_own_pending_request_only(self):
        organization, _ = self._make_organization()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        affiliation_services.submit_join_request(
            caregiver_profile=caregiver, code=organization.code, tenant_id=self.tenant.id
        )

        other_caregiver = CaregiverProfile.objects.get(user=self.other_provider_user)
        other_org, _ = self._make_organization(code="other-join-co", name="Different Co")
        affiliation_services.submit_join_request(
            caregiver_profile=other_caregiver,
            code=other_org.code,
            tenant_id=self.tenant.id,
        )

        self.login_as_provider()
        response = self.client.get("/provider/company/")
        self.assertContains(response, "Join Test Co")
        self.assertNotContains(response, "Different Co")


class CompanyRequestCancelViewTest(_CompanyFixtureMixin, ProviderPortalTestCase):
    def test_cancel_own_request(self):
        organization, _ = self._make_organization()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        req = affiliation_services.submit_join_request(
            caregiver_profile=caregiver,
            code=organization.code,
            tenant_id=self.tenant.id,
        )
        self.login_as_provider()
        response = self.client.post(f"/provider/company/requests/{req.id}/cancel/")
        self.assertRedirects(response, "/provider/company/")

        req.refresh_from_db()
        self.assertEqual(req.status, "cancelled")

    def test_cannot_cancel_another_caregivers_request(self):
        organization, _ = self._make_organization()
        other_caregiver = CaregiverProfile.objects.get(user=self.other_provider_user)
        req = affiliation_services.submit_join_request(
            caregiver_profile=other_caregiver,
            code=organization.code,
            tenant_id=self.tenant.id,
        )
        self.login_as_provider()
        response = self.client.post(f"/provider/company/requests/{req.id}/cancel/")
        self.assertRedirects(response, "/provider/company/")

        req.refresh_from_db()
        self.assertEqual(req.status, "pending")


class CompanyInvitationViewTest(_CompanyFixtureMixin, ProviderPortalTestCase):
    def test_accept_invitation(self):
        organization, admin_user = self._make_organization()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        membership = affiliation_services.invite_caregiver(
            organization=organization,
            caregiver_phone=caregiver.phone,
            invited_by=admin_user,
        )
        self.login_as_provider()
        response = self.client.post(f"/provider/company/invitations/{membership.id}/accept/")
        self.assertRedirects(response, "/provider/company/")

        membership.refresh_from_db()
        caregiver.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.ACTIVE)
        self.assertEqual(caregiver.provider_type, CaregiverProviderType.ORGANIZATION_AFFILIATED)

    def test_decline_invitation(self):
        organization, admin_user = self._make_organization()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        membership = affiliation_services.invite_caregiver(
            organization=organization,
            caregiver_phone=caregiver.phone,
            invited_by=admin_user,
        )
        self.login_as_provider()
        response = self.client.post(f"/provider/company/invitations/{membership.id}/decline/")
        self.assertRedirects(response, "/provider/company/")

        membership.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.REMOVED)

    def test_other_caregiver_cannot_accept_someone_elses_invitation(self):
        organization, admin_user = self._make_organization()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        membership = affiliation_services.invite_caregiver(
            organization=organization,
            caregiver_phone=caregiver.phone,
            invited_by=admin_user,
        )
        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/company/invitations/{membership.id}/accept/")
        self.assertRedirects(response, "/provider/company/")

        membership.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.PENDING)


class CompanyLeaveViewTest(_CompanyFixtureMixin, ProviderPortalTestCase):
    def test_leave_own_company(self):
        organization, admin_user = self._make_organization()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        req = affiliation_services.submit_join_request(
            caregiver_profile=caregiver,
            code=organization.code,
            tenant_id=self.tenant.id,
        )
        affiliation_services.approve_affiliation_request(request_id=req.id, reviewed_by=admin_user)
        membership = OrganizationMembership.objects.get(organization=organization, user=self.provider_user)

        self.login_as_provider()
        response = self.client.post(f"/provider/company/{membership.id}/leave/")
        self.assertRedirects(response, "/provider/company/")

        membership.refresh_from_db()
        caregiver.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.REMOVED)
        self.assertEqual(caregiver.provider_type, CaregiverProviderType.INDEPENDENT)

    def test_other_caregiver_cannot_leave_someone_elses_membership(self):
        organization, admin_user = self._make_organization()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        req = affiliation_services.submit_join_request(
            caregiver_profile=caregiver,
            code=organization.code,
            tenant_id=self.tenant.id,
        )
        affiliation_services.approve_affiliation_request(request_id=req.id, reviewed_by=admin_user)
        membership = OrganizationMembership.objects.get(organization=organization, user=self.provider_user)

        self.client.force_login(self.other_provider_user)
        response = self.client.post(f"/provider/company/{membership.id}/leave/")
        self.assertRedirects(response, "/provider/company/")

        membership.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.ACTIVE)
