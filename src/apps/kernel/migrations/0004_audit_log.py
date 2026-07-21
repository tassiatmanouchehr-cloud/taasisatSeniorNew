"""
Create the AuditLog model — append-only audit records.

Table: kernel.audit_log
"""

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0003_event_outbox"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("actor_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("actor_type", models.CharField(blank=True, max_length=50)),
                ("actor_display", models.CharField(blank=True, max_length=255)),
                ("impersonator_id", models.UUIDField(blank=True, null=True)),
                ("action", models.CharField(db_index=True, max_length=200)),
                ("module_id", models.CharField(max_length=10)),
                ("resource_type", models.CharField(db_index=True, max_length=100)),
                ("resource_id", models.UUIDField(blank=True, null=True)),
                ("before_snapshot", models.JSONField(blank=True, null=True)),
                ("after_snapshot", models.JSONField(blank=True, null=True)),
                ("reason", models.TextField(blank=True)),
                ("correlation_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=500)),
                (
                    "audit_class",
                    models.CharField(
                        choices=[
                            ("standard", "Standard"),
                            ("financial", "Financial"),
                            ("security", "Security"),
                            ("compliance", "Compliance"),
                        ],
                        db_index=True,
                        default="standard",
                        max_length=20,
                    ),
                ),
                ("retention_policy", models.CharField(default="standard", max_length=50)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Audit Log",
                "verbose_name_plural": "Audit Log Entries",
                "db_table": 'kernel"."audit_log',
                "ordering": ["-occurred_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "occurred_at"], name="idx_audit_tenant_time"),
                    models.Index(fields=["actor_id", "occurred_at"], name="idx_audit_actor_time"),
                    models.Index(fields=["resource_type", "resource_id"], name="idx_audit_resource"),
                    models.Index(fields=["action", "occurred_at"], name="idx_audit_action_time"),
                ],
            },
        ),
    ]
