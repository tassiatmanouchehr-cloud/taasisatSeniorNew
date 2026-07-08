"""Shared fixtures for availability tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)


class AvailabilityTestCase(TestCase):
    """Base test case providing a tenant, a second tenant, and supplier factories."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"avail-{uuid.uuid4().hex[:8]}", name="Availability Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"avail-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

    def _create_supplier(self, *, tenant=None, supplier_type=SupplierType.INDEPENDENT_PROVIDER, **kwargs) -> ServiceSupplier:
        tenant = tenant or self.tenant
        defaults = {
            "tenant_id": tenant.id,
            "supplier_type": supplier_type,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": SupplierStatus.ACTIVE,
            "availability_status": AvailabilityStatus.AVAILABLE,
            "verification_level": VerificationLevel.BASIC,
            "service_categories": [],
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)
