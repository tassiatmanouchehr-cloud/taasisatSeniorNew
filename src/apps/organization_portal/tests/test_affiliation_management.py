"""Phase 3 Sprint 3.1 — organization_portal's affiliation-management
views (staff page's new invite/approve/reject/terminate/cancel actions)."""

import uuid

from apps.accounts.models.profiles import (
    AffiliationStatus,
    CaregiverProfile,
    CompanyAffiliationRequest,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services import affiliations as affiliation_services

from .helpers import OrganizationPortalTestCase


class InviteCaregiverViewTest(OrganizationPortalTestCase):
    def test_invite_creates_pending_membership(self):
        person_phone = "09121110020"
        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="New Caregiver")
        user = UserAccount.objects.create_user(phone=person_phone, person=person, tenant=self.tenant)
        CaregiverProfile.objects.create(user=user, person=person, phone=person_phone, display_name="New Caregiver")

        self.login_as_admin()
        response = self.client.post("/organization/staff/invite/", {"phone": person_phone})
        self.assertRedirects(response, "/organization/staff/")

        membership = OrganizationMembership.objects.get(organization=self.organization, user=user)
        self.assertEqual(membership.status, OrgMembershipStatus.PENDING)
        self.assertEqual(membership.invited_by, self.admin_user)

    def test_non_admin_cannot_invite(self):
        self.client.force_login(self.non_admin_user)
        response = self.client.post("/organization/staff/invite/", {"phone": "09121110021"})
        self.assertEqual(response.status_code, 403)


class AffiliationRequestReviewViewTest(OrganizationPortalTestCase):
    def setUp(self):
        super().setUp()
        self.caregiver_phone = "09121110022"
        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="Requesting Caregiver")
        self.requesting_user = UserAccount.objects.create_user(phone=self.caregiver_phone, person=person, tenant=self.tenant)
        self.requesting_caregiver = CaregiverProfile.objects.create(
            user=self.requesting_user, person=person, phone=self.caregiver_phone, display_name="Requesting Caregiver",
        )
        self.request = affiliation_services.submit_join_request(
            caregiver_profile=self.requesting_caregiver, code=self.organization.code, tenant_id=self.tenant.id,
        )

    def test_approve_activates_membership(self):
        self.login_as_admin()
        response = self.client.post(f"/organization/staff/requests/{self.request.id}/approve/")
        self.assertRedirects(response, "/organization/staff/")

        self.request.refresh_from_db()
        self.assertEqual(self.request.status, AffiliationStatus.APPROVED)
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization=self.organization, user=self.requesting_user, status=OrgMembershipStatus.ACTIVE,
            ).exists(),
        )

    def test_reject_keeps_request_rejected(self):
        self.login_as_admin()
        response = self.client.post(f"/organization/staff/requests/{self.request.id}/reject/")
        self.assertRedirects(response, "/organization/staff/")

        self.request.refresh_from_db()
        self.assertEqual(self.request.status, AffiliationStatus.REJECTED)

    def test_another_organizations_admin_cannot_approve(self):
        other_admin = self._create_user(tenant=self.tenant, phone="09121110023")
        other_org = OrganizationProfile.objects.create(
            name="Other Org", code="other-review-org", admin_user=other_admin, tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org, user=other_admin, role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )
        self.client.force_login(other_admin)
        response = self.client.post(f"/organization/staff/requests/{self.request.id}/approve/")
        self.assertEqual(response.status_code, 404)

        self.request.refresh_from_db()
        self.assertEqual(self.request.status, AffiliationStatus.PENDING)

    def test_customer_cannot_access_staff_page(self):
        self.client.force_login(self.customer_user)
        response = self.client.get("/organization/staff/")
        self.assertEqual(response.status_code, 403)


class StaffTerminateViewTest(OrganizationPortalTestCase):
    def test_terminate_active_membership(self):
        self.login_as_admin()
        response = self.client.post(f"/organization/staff/{self.staff_membership.id}/terminate/")
        self.assertRedirects(response, "/organization/staff/")

        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, OrgMembershipStatus.REMOVED)
        self.assertIsNotNone(self.staff_membership.terminated_at)

    def test_another_organizations_admin_cannot_terminate(self):
        other_admin = self._create_user(tenant=self.tenant, phone="09121110024")
        other_org = OrganizationProfile.objects.create(
            name="Other Org 2", code="other-term-org", admin_user=other_admin, tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org, user=other_admin, role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )
        self.client.force_login(other_admin)
        response = self.client.post(f"/organization/staff/{self.staff_membership.id}/terminate/")
        self.assertEqual(response.status_code, 404)

        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, OrgMembershipStatus.ACTIVE)


class InvitationCancelViewTest(OrganizationPortalTestCase):
    def test_cancel_own_invitation(self):
        from apps.kernel.models import Person, UserAccount

        phone = "09121110025"
        person = Person.objects.create(tenant=self.tenant, full_name="Invitee")
        invitee_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        CaregiverProfile.objects.create(user=invitee_user, person=person, phone=phone, display_name="Invitee")

        membership = affiliation_services.invite_caregiver(
            organization=self.organization, caregiver_phone=phone, invited_by=self.admin_user,
        )
        self.login_as_admin()
        response = self.client.post(f"/organization/staff/invitations/{membership.id}/cancel/")
        self.assertRedirects(response, "/organization/staff/")

        membership.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.REMOVED)
