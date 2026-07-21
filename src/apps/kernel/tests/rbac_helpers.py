"""Shared RBAC fixtures for Module 08 tests (not a test module itself)."""

import uuid

from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount


def make_tenant(prefix="rbac") -> Tenant:
    return Tenant.objects.create(slug=f"{prefix}-{uuid.uuid4().hex[:8]}", name=f"{prefix} tenant")


def make_actor(tenant: Tenant, *, phone=None, full_name="Test Actor") -> UserAccount:
    phone = phone or f"0912{uuid.uuid4().hex[:7]}"
    person = Person.objects.create(tenant=tenant, full_name=full_name)
    return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)


def grant_permissions(
    tenant: Tenant, user: UserAccount, permission_keys, *, scope_type="", scope_id=None, is_active=True, expires_at=None
) -> RoleAssignment:
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
        scope_type=scope_type,
        scope_id=scope_id,
        is_active=is_active,
        expires_at=expires_at,
    )
