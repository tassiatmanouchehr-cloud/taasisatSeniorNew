"""
Initial kernel migration — creates PostgreSQL schemas, Tenant, Person, UserAccount.

This MUST be the first migration in the kernel app because Django's admin
requires AUTH_USER_MODEL to be created in the app's initial migration.

AUTH_USER_MODEL = "kernel.UserAccount"

Django's admin.0001_initial depends on:
  migrations.swappable_dependency(settings.AUTH_USER_MODEL)
  → resolves to ("kernel", "__first__")
  → which means the first migration(s) with initial=True

This migration creates (in order):
1. All 23 PostgreSQL schemas (RunSQL)
2. Tenant model (root of multi-tenancy)
3. Person model (stable identity)
4. UserAccount model (authentication, extends AbstractBaseUser)

References:
- ADR-001.01 (Person separate from UserAccount)
- ADR-001.12 (Tenant isolation mandatory)
- ADR-001.18 (PostgreSQL schemas separated by domain)
"""

import uuid

import django.contrib.auth.models
import django.db.models.deletion
from django.db import migrations, models

# --- PostgreSQL Schema Creation ---
# All 23 schemas per PHASE_0_5_ENTERPRISE_DOMAIN_MODEL_FREEZE.md Deliverable 15
SCHEMAS = [
    "kernel",
    "identity",
    "organizations",
    "catalog",
    "availability",
    "pricing",
    "marketplace",
    "orders",
    "execution",
    "financial",
    "communication",
    "trust",
    "documents",
    "incentives",
    "search",
    "geospatial",
    "analytics",
    "integration",
    "workflow",
    "jobs",
    "observability",
    "localization",
    "audit",
]

CREATE_SCHEMAS_SQL = "\n".join(f"CREATE SCHEMA IF NOT EXISTS {schema};" for schema in SCHEMAS)

DROP_SCHEMAS_SQL = "\n".join(f"DROP SCHEMA IF EXISTS {schema} CASCADE;" for schema in reversed(SCHEMAS))


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Step 1: Create all PostgreSQL schemas
        migrations.RunSQL(
            sql=CREATE_SCHEMAS_SQL,
            reverse_sql=DROP_SCHEMAS_SQL,
        ),
        # Step 2: Create Tenant model
        migrations.CreateModel(
            name="Tenant",
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
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                (
                    "domain",
                    models.CharField(
                        blank=True,
                        help_text="Optional custom domain for this tenant",
                        max_length=255,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("archived", "Archived"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "settings",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Tenant-level configuration overrides (JSONB)",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional tenant metadata",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.IntegerField(default=1)),
            ],
            options={
                "verbose_name": "Tenant",
                "verbose_name_plural": "Tenants",
                "db_table": 'kernel"."tenant',
                "ordering": ["name"],
            },
        ),
        # Step 3: Create Person model
        migrations.CreateModel(
            name="Person",
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
                ("full_name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("deactivated", "Deactivated")],
                        db_index=True,
                        default="active",
                        max_length=20,
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
                        related_name="persons",
                        to="kernel.tenant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Person",
                "verbose_name_plural": "Persons",
                "db_table": 'kernel"."person',
            },
        ),
        # Step 4: Create UserAccount model (AUTH_USER_MODEL)
        migrations.CreateModel(
            name="UserAccount",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(blank=True, null=True, verbose_name="last login"),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("email", models.EmailField(blank=True, max_length=255)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether this user can access the admin site.",
                    ),
                ),
                ("date_joined", models.DateTimeField(auto_now_add=True)),
                (
                    "person",
                    models.ForeignKey(
                        blank=True,
                        help_text="The Person this account belongs to. Null for initial superuser only.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="accounts",
                        to="kernel.person",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        help_text="Tenant this account belongs to. Null for platform superuser only.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_accounts",
                        to="kernel.tenant",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="useraccount_set",
                        related_query_name="useraccount",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="useraccount_set",
                        related_query_name="useraccount",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Account",
                "verbose_name_plural": "User Accounts",
                "db_table": 'kernel"."user_account',
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
