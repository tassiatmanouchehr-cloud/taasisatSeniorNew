from django.apps import apps as django_apps
from django.test import TestCase


class AdminPortalAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.admin_portal"))

    def test_core_modules_import_cleanly(self):
        from apps.admin_portal import permission_keys, views  # noqa: F401
        from apps.admin_portal.permissions import (  # noqa: F401
            require_admin_permission,
            require_authenticated,
            resolve_tenant_id,
        )

    def test_permission_key_constants(self):
        from apps.admin_portal import permission_keys

        self.assertEqual(permission_keys.PORTAL_ACCESS, "admin.portal.access")
        self.assertEqual(permission_keys.TENANTS_READ, "admin.tenants.read")
        self.assertEqual(permission_keys.SUPPLIERS_READ, "admin.suppliers.read")
        self.assertEqual(permission_keys.ORDERS_READ, "admin.orders.read")
        self.assertEqual(permission_keys.FINANCE_READ, "admin.finance.read")
        self.assertEqual(permission_keys.SYSTEM_READ, "admin.system.read")
