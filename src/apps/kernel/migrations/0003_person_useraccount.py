"""
Create Person and UserAccount models.

Tables:
- kernel.person (stable identity)
- kernel.user_account (authentication, extends AbstractBaseUser)

Per ADR-001.01: Person is separate from UserAccount.
Per ADR-001.02: User is not Provider.
"""

import uuid

import django.contrib.auth.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("kernel", "0002_tenant"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
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
        migrations.CreateModel(
            name="UserAccount",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
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
