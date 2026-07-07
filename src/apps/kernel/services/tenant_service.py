"""
Tenant Service — centralized default-tenant resolution.

Every module that needs a tenant context but has none supplied (e.g. legacy
single-tenant call sites, seed commands, demo data) must resolve it through
this service instead of hard-coding tenant slugs/names locally.

Per ADR-001.12: Every business record belongs to exactly one tenant.
Per Sprint 3A: default tenant helper centralized in kernel (single source
of truth — no per-app duplicates).
"""

import uuid

from apps.kernel.models.tenant import Tenant, TenantStatus

DEFAULT_TENANT_SLUG = "salmandyar"
DEFAULT_TENANT_NAME = "سالمندیار"


class TenantService:
    """Central resolver for the platform's default tenant."""

    @classmethod
    def get_default_tenant(cls) -> Tenant:
        """Get or create the platform default tenant (idempotent)."""
        tenant, _ = Tenant.objects.get_or_create(
            slug=DEFAULT_TENANT_SLUG,
            defaults={"name": DEFAULT_TENANT_NAME, "status": TenantStatus.ACTIVE},
        )
        return tenant

    @classmethod
    def get_default_tenant_id(cls) -> uuid.UUID:
        """Get or create the default tenant and return its id."""
        return cls.get_default_tenant().id
