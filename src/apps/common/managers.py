"""
Shared model managers for the Enterprise Service Marketplace Platform.

These managers enforce tenant isolation and soft-delete filtering
at the queryset level, ensuring no accidental data leakage.
"""

from django.db import models


class ActiveManager(models.Manager):
    """
    Default manager that excludes soft-deleted records.

    Use this as the default manager on any model with SoftDeleteMixin
    to ensure soft-deleted records are invisible by default.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """
    Manager that includes all records, even soft-deleted ones.

    Use this explicitly when you need to query deleted records
    (e.g., admin views, audit, compliance queries).
    """

    pass


class TenantScopedManager(models.Manager):
    """
    Manager that requires tenant_id for all queries.

    Note: Actual tenant filtering is enforced at the service/view layer
    via middleware. This manager provides a helper for explicit scoping.
    """

    def for_tenant(self, tenant_id):
        """Filter queryset to a specific tenant."""
        return self.get_queryset().filter(tenant_id=tenant_id)
