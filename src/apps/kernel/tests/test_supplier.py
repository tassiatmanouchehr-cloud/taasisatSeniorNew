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

import threading
import uuid

from django.apps import apps as django_apps
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase

from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
)
from apps.kernel.models.tenant import Tenant
from apps.kernel.services.supplier_registry import SupplierRegistry
from apps.kernel.services.supplier_resolver import SupplierResolver


class ServiceSupplierModelTest(TestCase):
    """Test ServiceSupplier model."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug="test-supplier-model", name="Test Tenant")
        self.tenant_id = self.tenant.id

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
        self.tenant = Tenant.objects.create(slug="test-supplier-resolver", name="Test Tenant")
        self.tenant_id = self.tenant.id
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


class ServiceSupplierUniqueConstraintTest(TestCase):
    """Core Profile-ServiceSupplier Invariant Remediation, Phase 7/8:
    proves the database itself — not just get_or_create()'s own
    check-then-act logic — rejects a duplicate (linked_entity_id,
    linked_entity_type) pair."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug="test-supplier-unique", name="Test Tenant")
        self.linked_entity_id = uuid.uuid4()

    def _create(self, **overrides):
        defaults = {
            "tenant_id": self.tenant.id,
            "supplier_type": SupplierType.INDEPENDENT_PROVIDER,
            "linked_entity_id": self.linked_entity_id,
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": SupplierStatus.ACTIVE,
        }
        defaults.update(overrides)
        return ServiceSupplier.objects.create(**defaults)

    def test_duplicate_linked_entity_pair_rejected_by_database(self):
        self._create()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._create(display_name="Second Row")

    def test_same_id_different_linked_type_is_allowed(self):
        """The constraint is on the (id, type) pair together — the same
        UUID legitimately reused across two different linked entity types
        is not a violation."""
        self._create(linked_entity_type="TestProfile")
        other = self._create(linked_entity_type="OtherProfile")
        self.assertIsNotNone(other.id)


class ServiceSupplierUniqueConstraintConcurrencyTest(TransactionTestCase):
    """Real concurrency, not a mocked exception: two threads racing to
    get_or_create the ServiceSupplier for the same (linked_entity_id,
    linked_entity_type) must leave exactly one row — proven against real
    PostgreSQL connections, mirroring
    apps.accounts.tests.test_profile_activation.ConcurrentActivationTest's
    own threading.Barrier pattern."""

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self.tenant = Tenant.objects.create(slug="test-supplier-concurrency", name="Test Tenant")
        self.linked_entity_id = uuid.uuid4()

    def test_concurrent_get_or_create_produces_exactly_one_row(self):
        barrier = threading.Barrier(2)
        errors = []

        def _race():
            try:
                barrier.wait(timeout=10)
                SupplierRegistry.get_or_create_supplier(
                    tenant_id=self.tenant.id,
                    linked_entity_id=self.linked_entity_id,
                    linked_entity_type="RaceProfile",
                    supplier_type=SupplierType.INDEPENDENT_PROVIDER,
                    display_name="Race Supplier",
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=_race) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [], f"neither racing call should raise unhandled: {errors}")
        count = ServiceSupplier.objects.filter(
            linked_entity_id=self.linked_entity_id, linked_entity_type="RaceProfile",
        ).count()
        self.assertEqual(count, 1, "concurrent get_or_create must produce exactly one ServiceSupplier row")
