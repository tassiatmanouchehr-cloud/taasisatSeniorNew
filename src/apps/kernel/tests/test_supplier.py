"""
Tests for ServiceSupplier model and SupplierResolver service.

Covers:
- Supplier creation with all three types
- Lifecycle transitions (activate, suspend, restore, deactivate)
- Invalid state transitions raise ValueError
- SupplierResolver respects marketplace model config
- Three marketplace models (independent_only, organization_only, hybrid)
- Version auto-increment on save
"""

import uuid

from django.test import TestCase

from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
)
from apps.kernel.services.supplier_resolver import SupplierResolver


class ServiceSupplierModelTest(TestCase):
    """Test ServiceSupplier model."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def _create_supplier(self, supplier_type=SupplierType.INDEPENDENT_PROVIDER, **kwargs):
        defaults = {
            "tenant_id": self.tenant_id,
            "supplier_type": supplier_type,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": SupplierStatus.PENDING,
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)

    def test_create_independent_provider(self):
        supplier = self._create_supplier(SupplierType.INDEPENDENT_PROVIDER)
        self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)
        self.assertEqual(supplier.status, SupplierStatus.PENDING)

    def test_create_organization(self):
        supplier = self._create_supplier(SupplierType.ORGANIZATION)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION)

    def test_create_organization_provider(self):
        supplier = self._create_supplier(SupplierType.ORGANIZATION_PROVIDER)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION_PROVIDER)

    def test_activate_from_pending(self):
        supplier = self._create_supplier()
        supplier.activate()
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)

    def test_suspend_from_active(self):
        supplier = self._create_supplier(status=SupplierStatus.ACTIVE)
        supplier.suspend()
        self.assertEqual(supplier.status, SupplierStatus.SUSPENDED)

    def test_restore_from_suspended(self):
        supplier = self._create_supplier(status=SupplierStatus.SUSPENDED)
        supplier.restore()
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)

    def test_deactivate_from_active(self):
        supplier = self._create_supplier(status=SupplierStatus.ACTIVE)
        supplier.deactivate()
        self.assertEqual(supplier.status, SupplierStatus.DEACTIVATED)

    def test_cannot_activate_deactivated(self):
        supplier = self._create_supplier(status=SupplierStatus.DEACTIVATED)
        with self.assertRaises(ValueError):
            supplier.activate()

    def test_cannot_suspend_pending(self):
        supplier = self._create_supplier(status=SupplierStatus.PENDING)
        with self.assertRaises(ValueError):
            supplier.suspend()

    def test_version_increments(self):
        supplier = self._create_supplier()
        self.assertEqual(supplier.version, 1)
        supplier.activate()
        supplier.refresh_from_db()
        self.assertEqual(supplier.version, 2)


class SupplierResolverTest(TestCase):
    """Test SupplierResolver with marketplace model config."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()
        # Register the marketplace config key
        self.config_key = ConfigurationKey.objects.create(
            key="marketplace.supplier_model",
            owner_module="M19",
            scope_level=ScopeLevel.TENANT,
            value_type=ValueType.ENUM,
            default_value="hybrid",
            allowed_values=["independent_only", "organization_only", "hybrid"],
        )

    def _create_supplier(self, supplier_type, status=SupplierStatus.ACTIVE):
        return ServiceSupplier.objects.create(
            tenant_id=self.tenant_id,
            supplier_type=supplier_type,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="TestProfile",
            display_name=f"Test {supplier_type}",
            status=status,
            availability_status=AvailabilityStatus.AVAILABLE,
        )

    def _set_marketplace_model(self, model_value):
        ConfigurationValue.objects.filter(
            tenant_id=self.tenant_id, config_key=self.config_key
        ).delete()
        ConfigurationValue.objects.create(
            tenant_id=self.tenant_id,
            config_key=self.config_key,
            scope_type=ScopeLevel.TENANT,
            value=model_value,
            is_active=True,
        )

    def test_hybrid_returns_all_types(self):
        self._set_marketplace_model("hybrid")
        self._create_supplier(SupplierType.INDEPENDENT_PROVIDER)
        self._create_supplier(SupplierType.ORGANIZATION)

        suppliers = SupplierResolver.get_active_suppliers(tenant_id=self.tenant_id)
        self.assertEqual(suppliers.count(), 2)

    def test_independent_only_filters_organizations(self):
        self._set_marketplace_model("independent_only")
        self._create_supplier(SupplierType.INDEPENDENT_PROVIDER)
        self._create_supplier(SupplierType.ORGANIZATION)

        suppliers = SupplierResolver.get_active_suppliers(tenant_id=self.tenant_id)
        self.assertEqual(suppliers.count(), 1)
        self.assertEqual(
            suppliers.first().supplier_type, SupplierType.INDEPENDENT_PROVIDER
        )

    def test_organization_only_filters_independent(self):
        self._set_marketplace_model("organization_only")
        self._create_supplier(SupplierType.INDEPENDENT_PROVIDER)
        self._create_supplier(SupplierType.ORGANIZATION)

        suppliers = SupplierResolver.get_active_suppliers(tenant_id=self.tenant_id)
        self.assertEqual(suppliers.count(), 1)
        self.assertEqual(suppliers.first().supplier_type, SupplierType.ORGANIZATION)

    def test_is_supplier_type_allowed_independent_only(self):
        self._set_marketplace_model("independent_only")
        self.assertTrue(
            SupplierResolver.is_supplier_type_allowed(
                tenant_id=self.tenant_id,
                supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            )
        )
        self.assertFalse(
            SupplierResolver.is_supplier_type_allowed(
                tenant_id=self.tenant_id,
                supplier_type=SupplierType.ORGANIZATION,
            )
        )

    def test_resolve_specific_supplier(self):
        supplier = self._create_supplier(SupplierType.INDEPENDENT_PROVIDER)
        resolved = SupplierResolver.resolve(supplier.id, tenant_id=self.tenant_id)
        self.assertEqual(resolved.id, supplier.id)

    def test_resolve_wrong_tenant_raises(self):
        supplier = self._create_supplier(SupplierType.INDEPENDENT_PROVIDER)
        other_tenant = uuid.uuid4()
        with self.assertRaises(ServiceSupplier.DoesNotExist):
            SupplierResolver.resolve(supplier.id, tenant_id=other_tenant)
