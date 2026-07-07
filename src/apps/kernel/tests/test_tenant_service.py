"""Tests for TenantService — the centralized default-tenant helper."""

from django.test import TestCase

from apps.kernel.models import Tenant
from apps.kernel.services.tenant_service import (
    DEFAULT_TENANT_NAME,
    DEFAULT_TENANT_SLUG,
    TenantService,
)


class TenantServiceTest(TestCase):
    """
    Note: the Sprint 3A data migration (orders.0003_backfill_tenant_and_supplier_data)
    already seeds the default tenant during test-database setup, so it always
    pre-exists here — these tests assert idempotency/resolution, not creation
    from a clean slate.
    """

    def test_returns_tenant_with_default_slug_and_name(self):
        tenant = TenantService.get_default_tenant()
        self.assertEqual(tenant.slug, DEFAULT_TENANT_SLUG)
        self.assertEqual(tenant.name, DEFAULT_TENANT_NAME)

    def test_idempotent_across_calls(self):
        first = TenantService.get_default_tenant()
        second = TenantService.get_default_tenant()
        self.assertEqual(first.id, second.id)
        self.assertEqual(Tenant.objects.filter(slug=DEFAULT_TENANT_SLUG).count(), 1)

    def test_get_default_tenant_id_matches_tenant(self):
        tenant = TenantService.get_default_tenant()
        tenant_id = TenantService.get_default_tenant_id()
        self.assertEqual(tenant_id, tenant.id)

    def test_does_not_duplicate_existing_tenant(self):
        existing = TenantService.get_default_tenant()
        tenant = TenantService.get_default_tenant()
        self.assertEqual(tenant.id, existing.id)
        self.assertEqual(Tenant.objects.filter(slug=DEFAULT_TENANT_SLUG).count(), 1)
