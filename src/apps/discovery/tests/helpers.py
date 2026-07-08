"""Shared fixtures for discovery tests (not a test module itself)."""

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
from apps.orders.models import CatalogStatus, ServiceCategory


class DiscoveryTestCase(TestCase):
    """Base test case providing a tenant, a second tenant, a service category, and supplier factories."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"disc-{uuid.uuid4().hex[:8]}", name="Discovery Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"disc-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.other_category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Companionship", slug="companionship", status=CatalogStatus.ACTIVE,
        )

    def _create_supplier(
        self, *, tenant=None, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
        verification_level=VerificationLevel.BASIC, service_categories=None, **kwargs,
    ) -> ServiceSupplier:
        tenant = tenant or self.tenant
        defaults = {
            "tenant_id": tenant.id,
            "supplier_type": supplier_type,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": status,
            "availability_status": availability_status,
            "verification_level": verification_level,
            "service_categories": service_categories if service_categories is not None else [str(self.category.id)],
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)

    def _create_caregiver_supplier(self, *, tenant=None, display_name="Caregiver", city=""):
        from apps.accounts.models.profiles import CaregiverProfile
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_caregiver
        from apps.kernel.models import Person, UserAccount

        tenant = tenant or self.tenant
        phone = f"0913{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        caregiver = CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name=display_name, city=city,
        )
        supplier = get_or_create_supplier_for_caregiver(caregiver, tenant_id=tenant.id)
        supplier.service_categories = [str(self.category.id)]
        supplier.status = SupplierStatus.ACTIVE
        supplier.availability_status = AvailabilityStatus.AVAILABLE
        supplier.save(update_fields=["service_categories", "status", "availability_status"])
        return supplier
