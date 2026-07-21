"""
Permission-key registry guardrails — Epic 05 (Permission-Key Registry &
Authorization Hardening).

Lightweight, source-inspection-based checks in the same style as
test_architecture_guardrails.py — deliberately conservative regex/AST
matching, not a policy engine. These are structural checks, not a
replacement for code review.
"""

import re
from pathlib import Path

from django.apps import apps as django_apps
from django.test import SimpleTestCase

from apps.kernel.permissions.registry import PermissionKey, PermissionRegistry, PermissionRegistryError, register

APPS_DIR = Path(django_apps.get_app_config("kernel").path).parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _python_files(*, under: Path, exclude_dirs: tuple[str, ...] = ()) -> list[Path]:
    files = []
    for path in under.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        files.append(path)
    return files


_RAW_LITERAL_CALL = re.compile(r"PermissionService\.(require|check)\(\s*[^,]*,\s*[\"']")


class NoRawLiteralPermissionKeysTest(SimpleTestCase):
    """No production PermissionService.require()/.check() call may pass a
    string literal as the permission_key argument — every real call site
    must import its key from a permission_keys.py facade (or, for
    apps.api/apps.admin_portal, receive it as a parameter already resolved
    from one)."""

    ALLOWED_DIR_PARTS = ("tests", "migrations")

    def test_no_string_literal_permission_key_arguments(self):
        offenders = []
        for path in _python_files(under=APPS_DIR, exclude_dirs=self.ALLOWED_DIR_PARTS):
            relative_parts = path.relative_to(APPS_DIR).parts
            if any(part in self.ALLOWED_DIR_PARTS for part in relative_parts):
                continue
            match = _RAW_LITERAL_CALL.search(_read(path))
            if match:
                offenders.append(f"{path.relative_to(APPS_DIR)}: {match.group(0)!r}")

        self.assertEqual(
            offenders,
            [],
            f"Found PermissionService.require()/.check() called with a raw string literal: {offenders}",
        )


class RegistryValidationTest(SimpleTestCase):
    def test_every_real_key_is_registered(self):
        """Every key that actually appears as a PermissionService argument
        (imported from a permission_keys.py facade) resolves in the
        registry — proven indirectly: every facade constant's value must
        be a registered key. apps.api.permission_keys is deliberately NOT
        imported here — apps.api sits at the apex of the dependency graph
        (docs/architecture/dependency-graph.md) and nothing outside
        apps/api/ may import it (see NoReverseApiImportTest in
        test_architecture_guardrails.py); the equivalent check for it
        lives in apps.api.tests instead."""
        from apps.accounts import permission_keys as accounts_keys
        from apps.admin_portal import permission_keys as admin_keys
        from apps.booking import permission_keys as booking_keys
        from apps.execution import permission_keys as execution_keys
        from apps.finance import permission_keys as finance_keys

        for module in (accounts_keys, admin_keys, booking_keys, execution_keys, finance_keys):
            for name in module.__all__:
                value = getattr(module, name)
                self.assertTrue(
                    PermissionRegistry.exists(value),
                    f"{module.__name__}.{name} = {value!r} is not registered in the canonical registry",
                )

    def test_duplicate_key_registration_raises(self):
        with self.assertRaises(PermissionRegistryError):
            PermissionRegistry.register(
                PermissionKey(
                    key="booking.assignment.assign",
                    domain="booking",
                    resource="assignment",
                    action="assign",
                    description="duplicate",
                )
            )

    def test_malformed_key_rejected(self):
        with self.assertRaises(PermissionRegistryError):
            register("Not-A-Valid-Key!", domain="x", resource="y", action="z", description="bad")

    def test_two_part_and_three_part_keys_both_valid(self):
        # Sanity check on the pattern itself — reviews.submit (2-part) and
        # booking.assignment.assign (3-part) both already registered.
        self.assertTrue(PermissionRegistry.exists("reviews.submit"))
        self.assertTrue(PermissionRegistry.exists("booking.assignment.assign"))

    def test_registry_has_no_duplicate_keys_by_construction(self):
        keys = PermissionRegistry.keys()
        self.assertEqual(len(keys), len(set(keys)))


class OrganizationScopedKeysRemainScopedTest(SimpleTestCase):
    """Epic 04's organization-isolation keys must stay marked
    organization_scope=True — a guardrail against silent metadata drift."""

    def test_organization_keys_are_marked_organization_scoped(self):
        for key in ("organization.membership.approve", "organization.membership.suspend", "booking.assignment.assign"):
            entry = PermissionRegistry.get(key)
            self.assertIsNotNone(entry)
            self.assertTrue(entry.organization_scope, f"{key} should be organization_scope=True")


class SeededRolePermissionsResolveTest(SimpleTestCase):
    """Every permission key seeded onto a Role by either role-seeding
    command must be a real, registered key — catches a typo or a
    retired/renamed key silently persisting in the shared catalog."""

    def test_all_role_catalog_permissions_are_registered(self):
        from apps.kernel.role_catalog import all_role_definitions

        unknown = []
        for role_def in all_role_definitions():
            for key in role_def.permissions:
                if not PermissionRegistry.exists(key):
                    unknown.append(f"{role_def.slug}: {key}")

        self.assertEqual(unknown, [], f"Role catalog grants unknown permission keys: {unknown}")

    def test_no_duplicate_slugs_within_a_single_catalog(self):
        from apps.kernel.role_catalog import DEFAULT_TENANT_ROLES, DEV_BOOTSTRAP_ROLES

        for catalog in (DEFAULT_TENANT_ROLES, DEV_BOOTSTRAP_ROLES):
            slugs = [role_def.slug for role_def in catalog]
            self.assertEqual(len(slugs), len(set(slugs)), f"Duplicate slug(s) in {catalog!r}")


class NoDependencyCycleFromPermissionsPackageTest(SimpleTestCase):
    """apps.kernel.permissions must import nothing outside the standard
    library / apps.kernel itself — it sits at the root of the dependency
    graph and must never import a business app."""

    def test_permissions_package_imports_nothing_from_business_apps(self):
        import ast

        business_apps = (
            "accounts",
            "orders",
            "matching",
            "booking",
            "execution",
            "finance",
            "wallet",
            "payments",
            "notifications",
            "reporting",
            "api",
            "portal",
            "provider_portal",
            "organization_portal",
            "admin_portal",
            "availability",
            "pricing",
            "discovery",
            "reviews",
        )
        permissions_dir = APPS_DIR / "kernel" / "permissions"
        for path in _python_files(under=permissions_dir):
            tree = ast.parse(_read(path))
            imported_modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.append(node.module)

            for module_name in imported_modules:
                for app in business_apps:
                    self.assertFalse(
                        module_name.startswith(f"apps.{app}"),
                        f"{path.relative_to(APPS_DIR)} imports {module_name!r} — kernel.permissions "
                        "sits at the root of the dependency graph and must not import a business app.",
                    )
