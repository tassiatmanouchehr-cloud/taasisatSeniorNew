"""
RBAC foundation models — Role, Permission, RoleAssignment.

Module 08 owns permission EVALUATION. This module (M25 Kernel) owns the
data structures. Other modules DEFINE protected operations by registering
Permission records; Module 08 evaluates them at runtime.

References:
- ADR-001.13 (RBAC evaluation belongs to Module 08)
- Phase 0.5 Deliverable 14 (Cross-Module Entity Ownership)
- Correction Package: Permission_Ownership_Model.md
"""

import uuid

from django.db import models
from django.db.models import Q


class Role(models.Model):
    """
    Named permission bundle — data-driven, not hard-coded.

    Roles are tenant-scoped and identified by slug. Organizations/tenants
    can create custom roles beyond the platform defaults.

    Per ADR-001.09: Organization hierarchy is data-driven.
    Roles are data rows, not Python enums.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="roles",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted or renamed by tenants.",
    )
    permissions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of permission keys assigned to this role.",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = 'kernel"."role'
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        unique_together = [("tenant", "slug")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)


class Permission(models.Model):
    """
    Protected operations registry.

    Each module registers its protected operations here. Module 08
    evaluates these at runtime. No module may independently decide
    whether an actor is authorized — only define what operations exist.

    Per ADR-001.13: RBAC evaluation belongs to Module 08.
    Per Correction Package: Permission_Ownership_Model.md.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(
        max_length=200,
        unique=True,
        help_text="Permission key, e.g., 'request.draft.create'",
    )
    module_id = models.CharField(
        max_length=10,
        help_text="Owning module, e.g., 'M01'",
    )
    resource_type = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    default_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Role slugs that have this permission by default.",
    )
    requires_scope = models.BooleanField(
        default=False,
        help_text="Whether this permission requires object-level scope evaluation.",
    )
    audit_required = models.BooleanField(
        default=True,
        help_text="Whether exercising this permission must be audited.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'kernel"."permission'
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["key"]

    def __str__(self):
        return self.key


class RoleAssignment(models.Model):
    """
    Binds a UserAccount to a Role within a scope.

    Scope defines where this role applies:
    - scope_type='platform' → platform-wide
    - scope_type='organization', scope_id=<org_id> → within an org
    - scope_type='branch', scope_id=<branch_id> → within a branch

    Per ADR-001.13: Module 08 evaluates role assignments.
    Per Phase 0.5 Deliverable 2: Memberships carry roles, roles carry permissions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    user = models.ForeignKey(
        "kernel.UserAccount",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    scope_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Scope: 'platform', 'organization', 'branch', 'department'",
    )
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the scoped entity (org, branch, dept). Null for platform scope.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="Person who granted this assignment.",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiry. Null means permanent until revoked.",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'kernel"."role_assignment'
        verbose_name = "Role Assignment"
        verbose_name_plural = "Role Assignments"
        indexes = [
            models.Index(fields=["tenant", "user", "is_active"]),
            models.Index(fields=["tenant", "role", "is_active"]),
            models.Index(fields=["scope_type", "scope_id"]),
        ]
        constraints = [
            # Database-level backstop (Epic 04 — Enterprise Organization
            # Isolation): the same (tenant, user, role, scope_type, scope_id)
            # combination can never have more than one ACTIVE row. Scoped to
            # is_active=True so a deactivated row never blocks a fresh grant
            # from being created afresh — apps.accounts.services
            # .organization_rbac.OrganizationRoleSyncService reactivates the
            # existing row in place instead, but this constraint is what
            # makes that safe under concurrent syncs, not just conventional.
            models.UniqueConstraint(
                fields=["tenant", "user", "role", "scope_type", "scope_id"],
                condition=Q(is_active=True),
                name="uq_role_assignment_active_scope",
            ),
        ]

    def __str__(self):
        scope = f" ({self.scope_type}:{self.scope_id})" if self.scope_type else ""
        return f"{self.user} → {self.role}{scope}"
