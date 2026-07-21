"""
Create PolicyDefinition and PolicyVersion models.

Tables: kernel.policy_definition, kernel.policy_version
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0006_feature_flag"),
    ]

    operations = [
        migrations.CreateModel(
            name="PolicyDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("policy_type", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("owner_module", models.CharField(max_length=10)),
                ("scope_type", models.CharField(blank=True, max_length=50)),
                ("scope_id", models.UUIDField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("deprecated", "Deprecated"),
                            ("archived", "Archived"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("current_version_number", models.IntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.IntegerField(default=1)),
            ],
            options={
                "verbose_name": "Policy Definition",
                "verbose_name_plural": "Policy Definitions",
                "db_table": 'kernel"."policy_definition',
                "ordering": ["policy_type", "name"],
                "unique_together": {("tenant_id", "policy_type", "name")},
                "indexes": [
                    models.Index(fields=["tenant_id", "policy_type", "status"], name="idx_policy_def_tenant_type"),
                ],
            },
        ),
        migrations.CreateModel(
            name="PolicyVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("version_number", models.IntegerField()),
                ("rule_payload", models.JSONField()),
                ("validation_schema", models.JSONField(blank=True, null=True)),
                ("effective_from", models.DateTimeField()),
                ("effective_until", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending_approval", "Pending Approval"),
                            ("active", "Active"),
                            ("superseded", "Superseded"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("approved_by", models.UUIDField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("change_reason", models.TextField(blank=True)),
                ("superseded_by", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.UUIDField(blank=True, null=True)),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="kernel.policydefinition",
                    ),
                ),
            ],
            options={
                "verbose_name": "Policy Version",
                "verbose_name_plural": "Policy Versions",
                "db_table": 'kernel"."policy_version',
                "ordering": ["-version_number"],
                "unique_together": {("policy", "version_number")},
                "indexes": [
                    models.Index(fields=["policy", "status", "effective_from"], name="idx_policy_ver_active"),
                    models.Index(fields=["tenant_id", "status"], name="idx_policy_ver_tenant"),
                ],
            },
        ),
    ]
