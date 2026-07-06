"""
Create the ServiceSupplier model.

Table: kernel.service_supplier
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kernel", "0009_policy"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceSupplier",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("supplier_type", models.CharField(choices=[("INDEPENDENT_PROVIDER", "Independent Provider"), ("ORGANIZATION", "Organization"), ("ORGANIZATION_PROVIDER", "Organization Provider")], db_index=True, max_length=30)),
                ("linked_entity_id", models.UUIDField()),
                ("linked_entity_type", models.CharField(max_length=100)),
                ("display_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("active", "Active"), ("suspended", "Suspended"), ("deactivated", "Deactivated")], db_index=True, default="pending", max_length=20)),
                ("capabilities", models.JSONField(blank=True, default=dict)),
                ("service_categories", models.JSONField(blank=True, default=list)),
                ("availability_status", models.CharField(choices=[("available", "Available"), ("busy", "Busy"), ("offline", "Offline"), ("on_leave", "On Leave")], default="offline", max_length=20)),
                ("verification_level", models.CharField(choices=[("unverified", "Unverified"), ("basic", "Basic"), ("advanced", "Advanced"), ("premium", "Premium")], default="unverified", max_length=20)),
                ("financial_party_id", models.UUIDField(blank=True, null=True)),
                ("reputation_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("external_ref", models.CharField(blank=True, max_length=255)),
                ("module_id", models.CharField(default="M25", max_length=10)),
                ("entity_type", models.CharField(default="ServiceSupplier", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.IntegerField(default=1)),
                ("created_by", models.UUIDField(blank=True, null=True)),
                ("updated_by", models.UUIDField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Service Supplier",
                "verbose_name_plural": "Service Suppliers",
                "db_table": 'kernel"."service_supplier',
                "ordering": ["display_name"],
                "indexes": [
                    models.Index(fields=["tenant_id", "supplier_type", "status"], name="idx_supplier_tenant_type_st"),
                    models.Index(fields=["tenant_id", "status", "availability_status"], name="idx_supplier_availability"),
                    models.Index(fields=["linked_entity_id", "linked_entity_type"], name="idx_supplier_linked_entity"),
                ],
            },
        ),
    ]
