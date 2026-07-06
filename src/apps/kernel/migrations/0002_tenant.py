"""
Create the Tenant model — root entity for multi-tenancy.

Table: kernel.tenant
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kernel", "0001_create_schemas"),
    ]

    operations = [
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
    ]
