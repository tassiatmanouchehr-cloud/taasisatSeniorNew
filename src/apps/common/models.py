"""
Abstract base models for the Enterprise Service Marketplace Platform.

All concrete models in the platform inherit from one or more of these bases.
They enforce the Global Identifier Standard (Module 25), tenant isolation,
soft-delete patterns, and optimistic concurrency.

References:
- ADR-001.12 (Tenant isolation mandatory)
- ADR-001.23 (Code follows frozen domain model)
- Phase 0.5 Deliverable 17 (Soft Delete Strategy)
"""

import uuid

from django.db import models
from django.utils import timezone

from .managers import ActiveManager, AllObjectsManager


class TimestampedModel(models.Model):
    """
    Abstract base providing created_at and updated_at timestamps.

    All platform entities carry these fields per the Global Identifier Standard.
    """

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantAwareModel(TimestampedModel):
    """
    Abstract base for all tenant-owned entities.

    Enforces:
    - UUID primary key (non-sequential, opaque)
    - Mandatory tenant_id (FK to kernel.Tenant, set in Commit 14)
    - Optimistic concurrency via version field
    - Actor tracking (created_by, updated_by)

    Per ADR-001.12: Every business record belongs to exactly one tenant.
    Per Global Identifier Standard: id, tenant_id, version, created_at, updated_at.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # tenant FK will be added when Tenant model exists (Commit 14)
    # For now, store as UUID to avoid circular dependency
    tenant_id = models.UUIDField(db_index=True)
    version = models.IntegerField(default=1)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            raise ValueError("tenant_id is required for all tenant-aware models")
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)


class SoftDeleteMixin(models.Model):
    """
    Mixin for soft-deletable entities.

    Instead of hard DELETE, records are marked with deleted_at timestamp.
    The ActiveManager filters these out by default.

    Per Phase 0.5 Deliverable 17 (Soft Delete Strategy).
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.UUIDField(null=True, blank=True)

    # Default manager excludes soft-deleted records
    objects = ActiveManager()
    # Explicit manager for including deleted records
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self, actor_id=None):
        """Mark this record as deleted without removing from database."""
        self.deleted_at = timezone.now()
        self.deleted_by = actor_id
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    @property
    def is_deleted(self):
        """Check if this record is soft-deleted."""
        return self.deleted_at is not None
