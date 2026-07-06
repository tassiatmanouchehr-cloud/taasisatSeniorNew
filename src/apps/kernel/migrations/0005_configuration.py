"""
Create ConfigurationKey and ConfigurationValue models — CCS system.

Tables: kernel.configuration_key, kernel.configuration_value
"""

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kernel", "0004_audit_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfigurationKey",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("key", models.CharField(db_index=True, max_length=200, unique=True)),
                ("owner_module", models.CharField(max_length=10)),
                ("schema_version", models.CharField(default="1.0", max_length=10)),
                ("scope_level", models.CharField(choices=[("platform", "Platform"), ("tenant", "Tenant"), ("organization", "Organization"), ("branch", "Branch"), ("role", "Role"), ("actor", "Actor")], default="tenant", max_length=20)),
                ("value_type", models.CharField(choices=[("boolean", "Boolean"), ("string", "String"), ("number", "Number"), ("integer", "Integer"), ("enum", "Enum"), ("object", "Object (JSON)"), ("array", "Array (JSON)")], default="string", max_length=20)),
                ("default_value", models.JSONField(blank=True, null=True)),
                ("allowed_values", models.JSONField(blank=True, null=True)),
                ("validation_schema", models.JSONField(blank=True, null=True)),
                ("override_policy", models.CharField(choices=[("locked", "Locked (no override allowed)"), ("inheritable", "Inheritable (child scopes inherit)"), ("tenant_override", "Tenant Override Allowed"), ("role_override", "Role Override Allowed"), ("full_override", "Full Override (any scope)")], default="tenant_override", max_length=20)),
                ("change_requires_approval", models.BooleanField(default=False)),
                ("activation_mode", models.CharField(choices=[("immediate", "Immediate"), ("scheduled", "Scheduled"), ("next_cycle", "Next Cycle")], default="immediate", max_length=20)),
                ("rollback_supported", models.BooleanField(default=True)),
                ("is_sensitive", models.BooleanField(default=False)),
                ("audit_class", models.CharField(default="standard", max_length=20)),
                ("description", models.TextField(blank=True)),
                ("deprecated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuration Key",
                "verbose_name_plural": "Configuration Keys",
                "db_table": 'kernel"."configuration_key',
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="ConfigurationValue",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("scope_type", models.CharField(choices=[("platform", "Platform"), ("tenant", "Tenant"), ("organization", "Organization"), ("branch", "Branch"), ("role", "Role"), ("actor", "Actor")], default="tenant", max_length=20)),
                ("scope_id", models.UUIDField(blank=True, null=True)),
                ("value", models.JSONField()),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("effective_from", models.DateTimeField(blank=True, null=True)),
                ("effective_until", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.UUIDField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("change_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.UUIDField(blank=True, null=True)),
                ("version", models.IntegerField(default=1)),
                ("config_key", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="overrides", to="kernel.configurationkey")),
            ],
            options={
                "verbose_name": "Configuration Value",
                "verbose_name_plural": "Configuration Values",
                "db_table": 'kernel"."configuration_value',
                "indexes": [
                    models.Index(fields=["tenant_id", "config_key", "is_active"], name="idx_config_val_tenant_key"),
                    models.Index(fields=["config_key", "scope_type", "scope_id"], name="idx_config_val_scope"),
                ],
            },
        ),
    ]
