"""
Tests for the seed_tenant management command — Module 21A.

Covers: usable admin credentials after seeding, admin-portal permissions
being granted in seed logic (not manually), and idempotency of the new
RoleAssignment/permission-granting behavior.
"""

import uuid

from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from apps.admin_portal.permission_keys import (
    FINANCE_READ,
    ORDERS_READ,
    PORTAL_ACCESS,
    SUPPLIERS_READ,
    SYSTEM_READ,
    TENANTS_READ,
)
from apps.admin_portal.permissions import require_admin_permission
from apps.kernel.models import Role, RoleAssignment, Tenant, UserAccount


class SeedTenantCreatesUsableAdminTest(TestCase):
    def test_creates_admin_with_usable_password(self):
        call_command("seed_tenant")
        user = UserAccount.objects.get(email="admin@marketplace.local")
        self.assertTrue(user.check_password("admin123456"))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_authenticate_works_after_seed(self):
        call_command("seed_tenant")
        user = authenticate(email="admin@marketplace.local", password="admin123456")
        self.assertIsNotNone(user)

    def test_idempotent(self):
        call_command("seed_tenant")
        call_command("seed_tenant")
        self.assertEqual(UserAccount.objects.filter(email="admin@marketplace.local").count(), 1)


class SeedTenantAdminPortalPermissionsTest(TestCase):
    """Admin portal access must work for the seeded admin, granted via seed logic."""

    def test_platform_owner_role_carries_admin_portal_permissions(self):
        call_command("seed_tenant")
        tenant = Tenant.objects.get(slug="dev")
        role = Role.objects.get(tenant=tenant, slug="platform-owner")
        for key in (PORTAL_ACCESS, TENANTS_READ, SUPPLIERS_READ, ORDERS_READ, FINANCE_READ, SYSTEM_READ):
            self.assertIn(key, role.permissions)

    def test_seeded_admin_has_role_assignment(self):
        call_command("seed_tenant")
        user = UserAccount.objects.get(email="admin@marketplace.local")
        tenant = Tenant.objects.get(slug="dev")
        assignment = RoleAssignment.objects.filter(tenant=tenant, user=user, role__slug="platform-owner").first()
        self.assertIsNotNone(assignment)
        self.assertTrue(assignment.is_active)

    def test_admin_portal_access_works_for_seeded_admin(self):
        call_command("seed_tenant")
        user = UserAccount.objects.get(email="admin@marketplace.local")

        request = RequestFactory().get("/")
        request.user = user

        tenant_id = require_admin_permission(request, PORTAL_ACCESS)
        self.assertEqual(tenant_id, user.tenant_id)

    def test_admin_portal_denied_without_permissions(self):
        tenant = Tenant.objects.create(slug=f"noperm-{uuid.uuid4().hex[:8]}", name="No Perm")
        from apps.kernel.models import Person

        person = Person.objects.create(tenant=tenant, full_name="No Perm User")
        user = UserAccount.objects.create_user(email="noperm@example.com", person=person, tenant=tenant)

        request = RequestFactory().get("/")
        request.user = user

        with self.assertRaises(PermissionDenied):
            require_admin_permission(request, PORTAL_ACCESS)

    def test_idempotent_permission_granting_does_not_duplicate(self):
        call_command("seed_tenant")
        call_command("seed_tenant")
        tenant = Tenant.objects.get(slug="dev")
        role = Role.objects.get(tenant=tenant, slug="platform-owner")
        self.assertEqual(role.permissions.count(PORTAL_ACCESS), 1)
