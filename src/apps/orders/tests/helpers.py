"""Shared test fixtures for orders tests (Sprint 5.1+)."""

import uuid

from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


def make_tenant(prefix="offer") -> Tenant:
    return Tenant.objects.create(
        slug=f"{prefix}-{uuid.uuid4().hex[:8]}",
        name=f"{prefix} tenant",
    )


def make_user(tenant: Tenant, *, phone=None) -> UserAccount:
    phone = phone or f"0912{uuid.uuid4().hex[:7]}"
    person = Person.objects.create(tenant=tenant, full_name="Test Actor")
    return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)


def make_supplier(tenant: Tenant, *, status=SupplierStatus.ACTIVE) -> ServiceSupplier:
    return ServiceSupplier.objects.create(
        tenant=tenant,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        linked_entity_id=uuid.uuid4(),
        linked_entity_type="TestProfile",
        status=status,
        availability_status=AvailabilityStatus.AVAILABLE,
        verification_level=VerificationLevel.BASIC,
        display_name=f"Test Supplier {uuid.uuid4().hex[:6]}",
    )


def make_order(tenant: Tenant, *, status=OrderStatus.NEW) -> Order:
    category = ServiceCategory.objects.create(
        tenant=tenant,
        name="Care",
        slug=f"care-{uuid.uuid4().hex[:6]}",
        status=CatalogStatus.ACTIVE,
    )
    return Order.objects.create(
        tenant=tenant,
        source=OrderSource.OPERATOR,
        status=status,
        service_category=category,
        description="Test order",
        city="tehran",
        address="Test address",
        phone="09120000000",
    )


def grant_permissions(tenant: Tenant, user: UserAccount, permission_keys) -> RoleAssignment:
    role = Role.objects.create(
        tenant=tenant,
        name="Test Role",
        slug=f"test-role-{uuid.uuid4().hex[:8]}",
        permissions=list(permission_keys),
    )
    return RoleAssignment.objects.create(
        tenant=tenant,
        user=user,
        role=role,
        is_active=True,
    )
