"""
Tenant model — the root entity for multi-tenancy.

Every business record in the platform belongs to exactly one tenant.
Tenants are isolated by default; cross-tenant access requires explicit
platform-level permission and audit classification.

References:
- ADR-001.12 (Tenant isolation mandatory)
- Phase 0.5 Deliverable 1, Section 1.1 (Tenant lifecycle)
- Module 25 Tenant_Boundary_Standard.md
"""

import uuid

from django.db import models


class TenantStatus(models.TextChoices):
    """Tenant lifecycle states."""

    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class Tenant(models.Model):
    """
    Root entity for multi-tenant isolation.

    Every tenant-aware entity in the platform carries a FK to this model.
    Platform-global records (e.g., Permission registry) do not have tenant_id.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional custom domain for this tenant",
    )
    status = models.CharField(
        max_length=20,
        choices=TenantStatus.choices,
        default=TenantStatus.ACTIVE,
        db_index=True,
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-level configuration overrides (JSONB)",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional tenant metadata",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "kernel\".\"tenant"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)
