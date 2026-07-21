"""
Tests for the kernel Supplier Registry — the single ownership point for
ServiceSupplier creation and lookup.

Covers:
- Creation/idempotency/lookup behavior.
- The registry stays completely generic (no vertical/accounts references).
- tenant_id referential integrity (FK to Tenant) is enforced at the DB level.
"""

import ast
import inspect
import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.models.tenant import Tenant
from apps.kernel.services import supplier_registry as supplier_registry_module
from apps.kernel.services.supplier_registry import SupplierRegistry


def _module_imports_accounts(module) -> bool:
    """True if `module`'s actual import statements reference apps.accounts.

    Uses the AST rather than a text scan so that mentioning "accounts" or
    "CaregiverProfile" in a docstring/comment (e.g. as a warning example)
    never produces a false positive.
    """
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.startswith("apps.accounts") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("apps.accounts"):
                return True
    return False


class SupplierRegistryTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="test-supplier-registry", name="Test Tenant")

    def test_get_or_create_supplier_creates_new(self):
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name="Generic Supplier",
        )
        self.assertEqual(ServiceSupplier.objects.count(), 1)
        self.assertEqual(supplier.tenant_id, self.tenant.id)

    def test_get_or_create_supplier_is_idempotent(self):
        entity_id = uuid.uuid4()
        first = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=entity_id,
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.ORGANIZATION,
            display_name="Generic Org",
        )
        second = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=entity_id,
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.ORGANIZATION,
            display_name="Generic Org",
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(ServiceSupplier.objects.count(), 1)

    def test_resolve_by_id_returns_supplier(self):
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name="X",
        )
        resolved = SupplierRegistry.resolve_by_id(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(resolved.id, supplier.id)

    def test_resolve_by_id_wrong_tenant_raises(self):
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name="X",
        )
        other_tenant = Tenant.objects.create(slug="test-supplier-registry-other", name="Other")
        with self.assertRaises(ServiceSupplier.DoesNotExist):
            SupplierRegistry.resolve_by_id(supplier.id, tenant_id=other_tenant.id)

    def test_find_by_linked_entity_returns_none_when_absent(self):
        self.assertIsNone(
            SupplierRegistry.find_by_linked_entity(linked_entity_id=uuid.uuid4(), linked_entity_type="GenericProfile")
        )

    def test_find_by_linked_entity_returns_existing(self):
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name="X",
        )
        found = SupplierRegistry.find_by_linked_entity(
            linked_entity_id=supplier.linked_entity_id,
            linked_entity_type="GenericProfile",
        )
        self.assertEqual(found.id, supplier.id)

    def test_create_rejects_unknown_tenant(self):
        """tenant_id is now a real FK — an unknown tenant must be rejected at the DB level."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            SupplierRegistry.get_or_create_supplier(
                tenant_id=uuid.uuid4(),
                linked_entity_id=uuid.uuid4(),
                linked_entity_type="GenericProfile",
                supplier_type=SupplierType.INDEPENDENT_PROVIDER,
                display_name="X",
            )

    def test_registry_module_stays_generic(self):
        """The registry must never import apps.accounts or vertical models."""
        self.assertFalse(_module_imports_accounts(supplier_registry_module))

    def test_set_status_updates_when_different(self):
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name="X",
            status=SupplierStatus.PENDING,
        )
        updated = SupplierRegistry.set_status(supplier, status=SupplierStatus.ACTIVE)
        self.assertEqual(updated.status, SupplierStatus.ACTIVE)
        supplier.refresh_from_db()
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)

    def test_set_status_is_idempotent_noop_when_unchanged(self):
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name="X",
            status=SupplierStatus.ACTIVE,
        )
        original_version = supplier.version
        updated = SupplierRegistry.set_status(supplier, status=SupplierStatus.ACTIVE)
        self.assertEqual(updated.version, original_version)

    def test_set_status_only_updates_status_field(self):
        supplier = SupplierRegistry.get_or_create_supplier(
            tenant_id=self.tenant.id,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="GenericProfile",
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            display_name="X",
            status=SupplierStatus.PENDING,
        )
        SupplierRegistry.set_status(supplier, status=SupplierStatus.SUSPENDED)
        supplier.refresh_from_db()
        self.assertEqual(supplier.display_name, "X")
        self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)
