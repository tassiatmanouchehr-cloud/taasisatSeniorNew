"""
Create RBAC models: Role, Permission, RoleAssignment.

Tables:
- kernel.role (named permission bundle, tenant-scoped)
- kernel.permission (protected operations registry, global)
- kernel.role_assignment (user-to-role binding with scope)

Per ADR-001.13: Module 08 evaluates; Kernel owns data structures.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(max_length=100)),
                ("description", models.TextField(blank=True)),
                (
                    "is_system",
                    models.BooleanField(
                        default=False,
                        help_text="System roles cannot be deleted or renamed by tenants.",
                    ),
                ),
                (
                    "permissions",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of permission keys assigned to this role.",
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.IntegerField(default=1)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="roles",
                        to="kernel.tenant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Role",
                "verbose_name_plural": "Roles",
                "db_table": 'kernel"."role',
                "ordering": ["name"],
                "unique_together": {("tenant", "slug")},
            },
        ),
        migrations.CreateModel(
            name="Permission",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        help_text="Permission key, e.g., 'request.draft.create'",
                        max_length=200,
                        unique=True,
                    ),
                ),
                (
                    "module_id",
                    models.CharField(
                        help_text="Owning module, e.g., 'M01'",
                        max_length=10,
                    ),
                ),
                ("resource_type", models.CharField(max_length=100)),
                ("action", models.CharField(max_length=50)),
                ("description", models.TextField(blank=True)),
                (
                    "default_roles",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Role slugs that have this permission by default.",
                    ),
                ),
                (
                    "requires_scope",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this permission requires object-level scope evaluation.",
                    ),
                ),
                (
                    "audit_required",
                    models.BooleanField(
                        default=True,
                        help_text="Whether exercising this permission must be audited.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Permission",
                "verbose_name_plural": "Permissions",
                "db_table": 'kernel"."permission',
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="RoleAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "scope_type",
                    models.CharField(
                        blank=True,
                        help_text="Scope: 'platform', 'organization', 'branch', 'department'",
                        max_length=50,
                    ),
                ),
                (
                    "scope_id",
                    models.UUIDField(
                        blank=True,
                        help_text="ID of the scoped entity. Null for platform scope.",
                        null=True,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "granted_by",
                    models.UUIDField(
                        blank=True,
                        help_text="Person who granted this assignment.",
                        null=True,
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Optional expiry. Null means permanent until revoked.",
                        null=True,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="role_assignments",
                        to="kernel.tenant",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="kernel.role",
                    ),
                ),
            ],
            options={
                "verbose_name": "Role Assignment",
                "verbose_name_plural": "Role Assignments",
                "db_table": 'kernel"."role_assignment',
                "indexes": [
                    models.Index(
                        fields=["tenant", "user", "is_active"],
                        name="kernel_ra_tenant_user_active",
                    ),
                    models.Index(
                        fields=["tenant", "role", "is_active"],
                        name="kernel_ra_tenant_role_active",
                    ),
                    models.Index(
                        fields=["scope_type", "scope_id"],
                        name="kernel_ra_scope",
                    ),
                ],
            },
        ),
    ]
