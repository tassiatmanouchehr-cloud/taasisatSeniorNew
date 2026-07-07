"""
Tests that RegistrationService consistently resolves the same centralized
default tenant (apps.kernel.services.tenant_service.TenantService) for every
registration path, instead of each call site defining its own tenant lookup.
"""

from django.test import TestCase

from apps.accounts.services.registration import RegistrationService
from apps.kernel.services.tenant_service import TenantService


class RegistrationTenantConsistencyTest(TestCase):
    def test_customer_uses_default_tenant(self):
        user, profile = RegistrationService.create_customer(
            phone="09121110001", full_name="Customer A",
        )
        default_tenant = TenantService.get_default_tenant()
        self.assertEqual(user.tenant_id, default_tenant.id)
        self.assertEqual(user.person.tenant_id, default_tenant.id)

    def test_caregiver_uses_default_tenant(self):
        user, profile, _ = RegistrationService.create_caregiver(
            phone="09121110002", full_name="Caregiver A",
        )
        default_tenant = TenantService.get_default_tenant()
        self.assertEqual(user.tenant_id, default_tenant.id)

    def test_company_admin_uses_default_tenant(self):
        user, organization = RegistrationService.create_company_admin(
            phone="09121110003", admin_name="Admin A", company_name="Org A",
        )
        default_tenant = TenantService.get_default_tenant()
        self.assertEqual(user.tenant_id, default_tenant.id)
        self.assertEqual(organization.tenant_id, default_tenant.id)

    def test_registration_module_has_no_local_tenant_helper(self):
        """The local _get_default_tenant() duplicate must be gone — kernel is the single source."""
        from apps.accounts.services import registration

        self.assertFalse(hasattr(registration, "_get_default_tenant"))
