"""Assignment center — manual staff assignment via the organization portal, Epic 02.

Epic 04 (Enterprise Organization Isolation) additions: eligibility
enforcement, cross-organization denial, and organization-scoped Assignment
Center visibility."""

from apps.booking.models import SupplierAssignment

from .helpers import OrganizationPortalTestCase


class AssignmentCenterViewTest(OrganizationPortalTestCase):
    def test_shows_open_order_and_available_staff(self):
        self.login_as_admin()
        response = self.client.get("/organization/assignments/")
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "Staff Caregiver")

    def test_assigned_order_no_longer_appears(self):
        from apps.accounts.services.provider_identity import resolve_supplier_for_user
        from apps.booking.services.assignment_service import AssignmentService

        supplier = resolve_supplier_for_user(self.caregiver_user)
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)

        self.login_as_admin()
        response = self.client.get("/organization/assignments/")
        self.assertNotContains(response, self.order.order_number)


class AssignStaffViewTest(OrganizationPortalTestCase):
    def test_assign_creates_supplier_assignment(self):
        self.login_as_admin()
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(self.staff_membership.id)},
        )
        self.assertRedirects(response, "/organization/assignments/")

        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.assigned_supplier_id)
        self.assertTrue(SupplierAssignment.objects.filter(order=self.order).exists())

    def test_cannot_assign_staff_from_another_organization(self):
        from apps.accounts.models.profiles import (
            OrganizationMembership,
            OrganizationProfile,
            OrgMembershipRole,
            OrgMembershipStatus,
        )

        other_org_admin = self._create_user(tenant=self.tenant, phone="09121110008")
        other_org = OrganizationProfile.objects.create(
            name="Other Co",
            code="other-co-3",
            admin_user=other_org_admin,
            tenant=self.tenant,
        )
        other_staff_user = self._create_user(tenant=self.tenant, phone="09121110009")
        other_membership = OrganizationMembership.objects.create(
            organization=other_org,
            user=other_staff_user,
            role_type=OrgMembershipRole.CAREGIVER,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.login_as_admin()
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(other_membership.id)},
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
                f"/organization/assignments/{self.order.id}/assign/",
                {"membership_id": str(self.staff_membership.id)},
            )

        self.assertTrue(AuditLog.objects.filter(action="domain_event.OrganizationAssignmentChanged").exists())


class AssignmentActorAndRbacTest(OrganizationPortalTestCase):
    """Enterprise Architecture Review follow-up, finding #5: the real
    organization admin — not "system" — must be the recorded actor for a
    manual assignment, whether or not organization-scoped RBAC seeding
    exists for them yet."""

    def test_unauthenticated_user_cannot_assign(self):
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(self.staff_membership.id)},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(SupplierAssignment.objects.filter(order=self.order).first())

    def test_non_admin_staff_member_cannot_assign(self):
        self.client.force_login(self.caregiver_user)
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(self.staff_membership.id)},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(SupplierAssignment.objects.filter(order=self.order).first())

    def test_admin_from_another_tenant_cannot_assign_this_orders_staff(self):
        """A cross-tenant attempt: an admin who administers an organization
        in a wholly different tenant, attempting to hit this order's assign
        URL with their own (tenant-B) staff membership. AssignmentService
        .assign()'s pre-existing _ensure_same_tenant check must reject it —
        the order belongs to tenant A, the resolved supplier to tenant B."""
        from apps.accounts.models.profiles import (
            CaregiverProfile,
            OrganizationMembership,
            OrganizationProfile,
            OrgMembershipRole,
            OrgMembershipStatus,
        )
        from apps.kernel.models import Person, Tenant, UserAccount

        other_tenant = Tenant.objects.create(slug="orgportal-cross-tenant", name="Cross Tenant")
        other_admin = UserAccount.objects.create_user(
            phone="09121119991",
            person=Person.objects.create(tenant=other_tenant, full_name="Other Admin"),
            tenant=other_tenant,
        )
        other_org = OrganizationProfile.objects.create(
            name="Cross Tenant Co",
            code="cross-tenant-co",
            admin_user=other_admin,
            tenant=other_tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=other_admin,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        other_staff_person = Person.objects.create(tenant=other_tenant, full_name="Cross Tenant Staff")
        other_staff_user = UserAccount.objects.create_user(
            phone="09121119992",
            person=other_staff_person,
            tenant=other_tenant,
        )
        CaregiverProfile.objects.create(
            user=other_staff_user,
            person=other_staff_person,
            phone="09121119992",
            display_name="Cross Tenant Staff",
        )
        other_membership = OrganizationMembership.objects.create(
            organization=other_org,
            user=other_staff_user,
            role_type=OrgMembershipRole.CAREGIVER,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.client.force_login(other_admin)
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(other_membership.id)},
        )
        self.assertEqual(response.status_code, 200)  # action_error.html, not a redirect

        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier_id)
        self.assertFalse(SupplierAssignment.objects.filter(order=self.order).exists())

    def test_assignment_records_the_real_admin_as_assigned_by(self):
        self.login_as_admin()
        self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(self.staff_membership.id)},
        )

        assignment = SupplierAssignment.objects.get(order=self.order)
        self.assertEqual(assignment.assigned_by_id, self.admin_user.id)

    def test_assignment_is_ownership_authorized_not_system_context(self):
        """No organization-scoped RBAC seeding exists for self.admin_user —
        the fallback must be an explicit, correctly-attributed
        'ownership_authorized' audit entry, never a 'system_context' one."""
        from apps.kernel.models.audit import AuditLog

        self.login_as_admin()
        self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(self.staff_membership.id)},
        )

        entry = AuditLog.objects.get(
            tenant_id=self.tenant.id,
            action="rbac.permission.ownership_authorized",
        )
        self.assertEqual(entry.actor_id, self.admin_user.person_id)
        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="rbac.permission.system_context").exists(),
        )

    def test_real_rbac_role_is_used_and_preferred_over_ownership_fallback(self):
        """If organization-scoped RBAC seeding DID exist for this admin
        (simulated here with a tenant-wide grant, since no seeding
        mechanism exists yet), the real permission check succeeds and the
        ownership-authorized fallback is never reached."""
        from apps.kernel.models.audit import AuditLog
        from apps.kernel.tests.rbac_helpers import grant_permissions

        grant_permissions(self.tenant, self.admin_user, ["booking.assignment.assign"])

        self.login_as_admin()
        self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(self.staff_membership.id)},
        )

        assignment = SupplierAssignment.objects.get(order=self.order)
        self.assertEqual(assignment.assigned_by_id, self.admin_user.id)
        self.assertFalse(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action="rbac.permission.ownership_authorized",
            ).exists(),
        )
        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="rbac.permission.system_context").exists(),
        )


class EligibilityEnforcementTest(OrganizationPortalTestCase):
    """Epic 04 (Enterprise Organization Isolation): the actual fix for
    GAP_ANALYSIS.md's "Organization Assignment Center is tenant-wide, not
    organization-scoped" finding."""

    def _revoke_default_eligibility(self):
        from apps.orders.services.eligibility_service import OrderEligibilityService

        OrderEligibilityService.revoke(order=self.order, organization=self.organization)

    def test_order_without_eligibility_is_absent_from_assignment_center(self):
        self._revoke_default_eligibility()
        self.login_as_admin()
        response = self.client.get("/organization/assignments/")
        self.assertNotContains(response, self.order.order_number)

    def test_cannot_assign_own_staff_to_ineligible_order(self):
        self._revoke_default_eligibility()
        self.login_as_admin()
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(self.staff_membership.id)},
        )
        self.assertEqual(response.status_code, 200)  # renders action_error.html, not a redirect

        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier_id)
        self.assertFalse(SupplierAssignment.objects.filter(order=self.order).exists())

    def test_second_organization_cannot_see_first_organizations_eligible_order(self):
        """Two organizations, one tenant: org B has no eligibility grant for
        org A's order and must not see it in its own Assignment Center."""
        from apps.accounts.models.profiles import (
            OrganizationMembership,
            OrganizationProfile,
            OrgMembershipRole,
            OrgMembershipStatus,
        )

        other_admin = self._create_user(tenant=self.tenant, phone="09121110010")
        other_org = OrganizationProfile.objects.create(
            name="Other Co",
            code="other-co-elig",
            admin_user=other_admin,
            tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=other_admin,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.client.force_login(other_admin)
        response = self.client.get("/organization/assignments/")
        self.assertNotContains(response, self.order.order_number)

    def test_second_organization_cannot_assign_to_first_organizations_order(self):
        from apps.accounts.models.profiles import (
            CaregiverProfile,
            OrganizationMembership,
            OrganizationProfile,
            OrgMembershipRole,
            OrgMembershipStatus,
        )

        other_admin = self._create_user(tenant=self.tenant, phone="09121110011")
        other_org = OrganizationProfile.objects.create(
            name="Other Co 2",
            code="other-co-elig-2",
            admin_user=other_admin,
            tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=other_admin,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )
        other_staff_user = self._create_user(tenant=self.tenant, phone="09121110012")
        CaregiverProfile.objects.create(
            user=other_staff_user,
            person=other_staff_user.person,
            phone="09121110012",
            display_name="Other Staff",
        )
        other_membership = OrganizationMembership.objects.create(
            organization=other_org,
            user=other_staff_user,
            role_type=OrgMembershipRole.CAREGIVER,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.client.force_login(other_admin)
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(other_membership.id)},
        )
        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier_id)

    def test_access_denial_publishes_audited_domain_event(self):
        from apps.kernel.models.audit import AuditLog

        self._revoke_default_eligibility()
        self.login_as_admin()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                f"/organization/assignments/{self.order.id}/assign/",
                {"membership_id": str(self.staff_membership.id)},
            )

        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action="domain_event.OrganizationAccessDenied",
            ).exists(),
        )

    def test_reassignment_to_own_organization_does_not_require_fresh_eligibility(self):
        """The reassignment case: once assigned to this organization's own
        staff, a later eligibility revoke must not block acting on it again
        (e.g. reassigning to a different staff member of the same org)."""
        from apps.accounts.models.profiles import (
            CaregiverProfile,
            OrganizationMembership,
            OrgMembershipRole,
            OrgMembershipStatus,
        )
        from apps.accounts.services.provider_identity import resolve_supplier_for_user
        from apps.booking.services.assignment_service import AssignmentService

        supplier = resolve_supplier_for_user(self.caregiver_user)
        AssignmentService.assign(order_id=self.order.id, supplier=supplier)
        self._revoke_default_eligibility()

        second_staff_user = self._create_user(tenant=self.tenant, phone="09121110013")
        CaregiverProfile.objects.create(
            user=second_staff_user,
            person=second_staff_user.person,
            phone="09121110013",
            display_name="Second Staff",
        )
        second_membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=second_staff_user,
            role_type=OrgMembershipRole.CAREGIVER,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.login_as_admin()
        response = self.client.post(
            f"/organization/assignments/{self.order.id}/assign/",
            {"membership_id": str(second_membership.id)},
        )
        self.assertRedirects(response, "/organization/assignments/")
