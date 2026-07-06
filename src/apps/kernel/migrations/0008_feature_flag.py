"""
Create the FeatureFlag model.

Table: kernel.feature_flag
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kernel", "0007_configuration"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeatureFlag",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("key", models.CharField(max_length=200)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("flag_type", models.CharField(choices=[("boolean", "Boolean (on/off)"), ("percentage", "Percentage Rollout"), ("actor_list", "Actor Allowlist"), ("rule_based", "Rule-Based (JSON rules)")], default="boolean", max_length=20)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("enabled", "Enabled"), ("disabled", "Disabled"), ("archived", "Archived")], db_index=True, default="draft", max_length=20)),
                ("is_enabled", models.BooleanField(default=False)),
                ("percentage", models.IntegerField(default=0)),
                ("actor_allowlist", models.JSONField(blank=True, default=list)),
                ("actor_blocklist", models.JSONField(blank=True, default=list)),
                ("targeting_rules", models.JSONField(blank=True, default=dict)),
                ("kill_switch", models.BooleanField(default=False)),
                ("owner_module", models.CharField(blank=True, max_length=10)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.IntegerField(default=1)),
            ],
            options={
                "verbose_name": "Feature Flag",
                "verbose_name_plural": "Feature Flags",
                "db_table": 'kernel"."feature_flag',
                "ordering": ["key"],
                "unique_together": {("tenant_id", "key")},
                "indexes": [
                    models.Index(fields=["tenant_id", "status"], name="idx_flag_tenant_status"),
                ],
            },
        ),
    ]
