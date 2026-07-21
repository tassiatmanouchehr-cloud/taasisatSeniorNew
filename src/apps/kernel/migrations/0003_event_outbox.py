"""
Create the EventOutbox model — CES transactional outbox.

Table: kernel.event_outbox
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0002_rbac"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventOutbox",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "event_type",
                    models.CharField(
                        db_index=True,
                        help_text="Fully qualified event type, e.g., 'Request.Created.v1'",
                        max_length=200,
                    ),
                ),
                ("event_version", models.CharField(default="1.0", max_length=10)),
                ("occurred_at", models.DateTimeField(help_text="When the business event actually occurred.")),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True, help_text="When the event was successfully dispatched.", null=True
                    ),
                ),
                (
                    "source_module",
                    models.CharField(help_text="Module that produced this event, e.g., 'M01'.", max_length=10),
                ),
                (
                    "source_entity_id",
                    models.UUIDField(blank=True, help_text="ID of the entity that changed.", null=True),
                ),
                (
                    "source_entity_type",
                    models.CharField(blank=True, help_text="Type of the entity that changed.", max_length=100),
                ),
                (
                    "actor_id",
                    models.UUIDField(blank=True, help_text="Person/system that caused this event.", null=True),
                ),
                ("actor_type", models.CharField(blank=True, help_text="Type of actor.", max_length=50)),
                (
                    "correlation_id",
                    models.UUIDField(db_index=True, help_text="Links related events across a request chain."),
                ),
                (
                    "causation_id",
                    models.UUIDField(blank=True, help_text="ID of the event that directly caused this one.", null=True),
                ),
                (
                    "idempotency_key",
                    models.CharField(
                        blank=True, db_index=True, help_text="Prevents duplicate processing.", max_length=255
                    ),
                ),
                (
                    "privacy_class",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("internal", "Internal"),
                            ("restricted", "Restricted"),
                            ("sensitive", "Sensitive"),
                        ],
                        default="internal",
                        max_length=20,
                    ),
                ),
                (
                    "audit_class",
                    models.CharField(
                        choices=[
                            ("none", "None"),
                            ("standard", "Standard"),
                            ("financial", "Financial"),
                            ("security", "Security"),
                            ("compliance", "Compliance"),
                        ],
                        default="standard",
                        max_length=20,
                    ),
                ),
                (
                    "schema_ref",
                    models.CharField(
                        blank=True, help_text="Reference to the JSON schema for this event's payload.", max_length=255
                    ),
                ),
                ("payload", models.JSONField(default=dict, help_text="Domain-specific event data.")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("published", "Published"),
                            ("failed", "Failed"),
                            ("dead_letter", "Dead Letter"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("retry_count", models.IntegerField(default=0)),
                ("max_retries", models.IntegerField(default=5)),
                (
                    "next_retry_at",
                    models.DateTimeField(blank=True, help_text="Scheduled time for next retry attempt.", null=True),
                ),
                ("error_message", models.TextField(blank=True, help_text="Last error encountered during publishing.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Event Outbox",
                "verbose_name_plural": "Event Outbox Entries",
                "db_table": 'kernel"."event_outbox',
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(fields=["status", "created_at"], name="idx_outbox_pending"),
                    models.Index(fields=["status", "next_retry_at"], name="idx_outbox_retry"),
                    models.Index(fields=["tenant_id", "event_type", "created_at"], name="idx_outbox_tenant_type"),
                ],
            },
        ),
    ]
