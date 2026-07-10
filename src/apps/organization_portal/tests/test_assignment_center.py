"""Assignment center — manual staff assignment via the organization portal, Epic 02."""

from apps.booking.models import SupplierAssignment

from .helpers import OrganizationPortalTestCase


class AssignmentCenterViewTest(OrganizationPortalTestCase):
    def test_shows_open_order_and_available_staff(self):
        self.login_as_admin()
        response = self.client.get("/organization/assignments/")
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "Staff Caregiver")

    def test_assigned_order_no_longer_appears(self):
        from apps.booking.services.assignment_service import AssignmentService
        from apps.accounts.services.provider_identity import resolve_supplier_for_user

        supplier = resolve_supplier_for_user(self.caregiver_user)
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)

        self.login_as_admin()
        response = self.client.get("/organization/assignments/")
        self.assertNotContains(response, self.order.order_number)


class AssignStaffViewTest(OrganizationPortalTestCase):
    def test_assign_creates_supplier_assignment(self):
        self.login_as_admin()
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/", {"membership_id": str(self.staff_membership.id)},
        )
        self.assertRedirects(response, "/organization/assignments/")

        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.assigned_supplier_id)
        self.assertTrue(SupplierAssignment.objects.filter(order=self.order).exists())

    def test_cannot_assign_staff_from_another_organization(self):
        from apps.accounts.models.profiles import OrganizationMembership, OrganizationProfile, OrgMembershipRole, OrgMembershipStatus

        other_org_admin = self._create_user(tenant=self.tenant, phone="09121110008")
        other_org = OrganizationProfile.objects.create(
            name="Other Co", code="other-co-3", admin_user=other_org_admin, tenant=self.tenant,
        )
        other_staff_user = self._create_user(tenant=self.tenant, phone="09121110009")
        other_membership = OrganizationMembership.objects.create(
            organization=other_org, user=other_staff_user,
            role_type=OrgMembershipRole.CAREGIVER, status=OrgMembershipStatus.ACTIVE,
        )

        self.login_as_admin()
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/", {"membership_id": str(other_membership.id)},
        )
        self.assertEqual(response.status_code, 200)  # renders action_error.html, not a redirect

        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier_id)


class AssignmentEventPublishingTest(OrganizationPortalTestCase):
    def test_assign_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        self.login_as_admin()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                f"/organization/assignments/{self.order.id}/assign/", {"membership_id": str(self.staff_membership.id)},
            )

        self.assertTrue(
            AuditLog.objects.filter(action="domain_event.OrganizationAssignmentChanged").exists()
        )
