"""Tests for management commands."""

from django.core.management import call_command
from django.test import TestCase

from apps.kernel.models import Role, RoleAssignment, Tenant, UserAccount


class SeedAuthRolesTest(TestCase):
    """Test seed_auth_roles management command."""

    def test_creates_roles(self):
        call_command("seed_auth_roles")
        tenant = Tenant.objects.get(slug="salmandyar")
        roles = Role.objects.filter(tenant=tenant)
        self.assertEqual(roles.count(), 12)

    def test_idempotent(self):
        call_command("seed_auth_roles")
        call_command("seed_auth_roles")
        tenant = Tenant.objects.get(slug="salmandyar")
        roles = Role.objects.filter(tenant=tenant)
        self.assertEqual(roles.count(), 12)

    def test_creates_expected_slugs(self):
        call_command("seed_auth_roles")
        tenant = Tenant.objects.get(slug="salmandyar")
        expected = {
            "platform_owner", "platform_admin", "platform_operator",
            "platform_support", "platform_accounting", "platform_security",
            "platform_it", "customer", "independent_caregiver",
            "organization_caregiver", "organization_admin", "organization_operator",
        }
        actual = set(Role.objects.filter(tenant=tenant).values_list("slug", flat=True))
        self.assertEqual(actual, expected)

    def test_organization_admin_gets_epic04_permissions(self):
        """Epic 04 (Enterprise Organization Isolation)."""
        call_command("seed_auth_roles")
        tenant = Tenant.objects.get(slug="salmandyar")
        role = Role.objects.get(tenant=tenant, slug="organization_admin")
        self.assertIn("organization.assignment.assign", role.permissions)
        self.assertIn("organization.membership.approve", role.permissions)
        self.assertIn("organization.membership.suspend", role.permissions)

    def test_rerun_preserves_tenant_customized_permission(self):
        """Additive merge: a permission a tenant granted manually must
        survive a re-run of this idempotent seed command."""
        call_command("seed_auth_roles")
        tenant = Tenant.objects.get(slug="salmandyar")
        role = Role.objects.get(tenant=tenant, slug="organization_admin")
        role.permissions = [*role.permissions, "organization.custom.thing"]
        role.save(update_fields=["permissions"])

        call_command("seed_auth_roles")
        role.refresh_from_db()
        self.assertIn("organization.custom.thing", role.permissions)
        self.assertIn("organization.assignment.assign", role.permissions)


class CreatePlatformOwnerTest(TestCase):
    """Test create_platform_owner management command."""

    def test_creates_owner(self):
        call_command("create_platform_owner", phone="09121111111", name="Manouchehr")
        user = UserAccount.objects.get(phone="09121111111")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.person.full_name, "Manouchehr")

    def test_assigns_platform_owner_role(self):
        call_command("create_platform_owner", phone="09121111111", name="Manouchehr")
        user = UserAccount.objects.get(phone="09121111111")
        assignment = RoleAssignment.objects.filter(user=user).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.role.slug, "platform_owner")

    def test_idempotent(self):
        call_command("create_platform_owner", phone="09121111111", name="Manouchehr")
        call_command("create_platform_owner", phone="09121111111", name="Manouchehr")
        count = UserAccount.objects.filter(phone="09121111111").count()
        self.assertEqual(count, 1)
