"""reconcile_role_permissions — Epic 05 (Permission-Key Registry & Authorization Hardening)."""

import uuid

from django.core.management import call_command
from django.test import TestCase

from apps.kernel.models import Role, Tenant
from apps.kernel.role_catalog import ORGANIZATION_ADMIN_PERMISSIONS, ORGANIZATION_ADMIN_ROLE_SLUG


class ReconcileRolePermissionsTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"reconcile-{uuid.uuid4().hex[:8]}", name="Reconcile Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"reconcile-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.role = Role.objects.create(
            tenant=self.tenant, slug=ORGANIZATION_ADMIN_ROLE_SLUG, name="مدیر سازمان", is_system=True,
            permissions=[],
        )
        self.other_role = Role.objects.create(
            tenant=self.other_tenant, slug=ORGANIZATION_ADMIN_ROLE_SLUG, name="مدیر سازمان", is_system=True,
            permissions=[],
        )

    def test_adds_missing_canonical_permissions(self):
        call_command("reconcile_role_permissions")
        self.role.refresh_from_db()
        for key in ORGANIZATION_ADMIN_PERMISSIONS:
            self.assertIn(key, self.role.permissions)

    def test_dry_run_writes_nothing(self):
        call_command("reconcile_role_permissions", "--dry-run")
        self.role.refresh_from_db()
        self.assertEqual(self.role.permissions, [])

    def test_preserves_custom_valid_permission(self):
        self.role.permissions = ["reviews.submit"]
        self.role.save(update_fields=["permissions"])

        call_command("reconcile_role_permissions")

        self.role.refresh_from_db()
        self.assertIn("reviews.submit", self.role.permissions)
        for key in ORGANIZATION_ADMIN_PERMISSIONS:
            self.assertIn(key, self.role.permissions)

    def test_unknown_permission_reported_but_not_removed_by_default(self):
        self.role.permissions = ["totally.made.up"]
        self.role.save(update_fields=["permissions"])

        call_command("reconcile_role_permissions")

        self.role.refresh_from_db()
        self.assertIn("totally.made.up", self.role.permissions)

    def test_unknown_permission_removed_with_explicit_flag(self):
        self.role.permissions = ["totally.made.up"]
        self.role.save(update_fields=["permissions"])

        call_command("reconcile_role_permissions", "--remove-unknown")

        self.role.refresh_from_db()
        self.assertNotIn("totally.made.up", self.role.permissions)

    def test_remove_unknown_never_removes_a_valid_custom_key(self):
        self.role.permissions = ["reviews.submit"]
        self.role.save(update_fields=["permissions"])

        call_command("reconcile_role_permissions", "--remove-unknown")

        self.role.refresh_from_db()
        self.assertIn("reviews.submit", self.role.permissions)

    def test_repeated_run_is_idempotent(self):
        call_command("reconcile_role_permissions")
        call_command("reconcile_role_permissions")

        self.role.refresh_from_db()
        for key in ORGANIZATION_ADMIN_PERMISSIONS:
            self.assertEqual(self.role.permissions.count(key), 1)

    def test_tenant_filter_limits_scope(self):
        call_command("reconcile_role_permissions", f"--tenant={self.tenant.slug}")

        self.role.refresh_from_db()
        self.other_role.refresh_from_db()
        self.assertNotEqual(self.role.permissions, [])
        self.assertEqual(self.other_role.permissions, [])

    def test_operates_independently_per_tenant(self):
        call_command("reconcile_role_permissions")

        self.role.refresh_from_db()
        self.other_role.refresh_from_db()
        for key in ORGANIZATION_ADMIN_PERMISSIONS:
            self.assertIn(key, self.role.permissions)
            self.assertIn(key, self.other_role.permissions)
