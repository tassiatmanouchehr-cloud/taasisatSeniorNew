"""
Sprint 3A — Schema step 1/3: add tenant_id (nullable) and assigned_supplier
to the catalog/order models, without touching the legacy assignment fields
yet. PostgreSQL cannot add a NOT NULL column to a populated table without a
default in a single step, so tenant_id starts nullable here and is enforced
NOT NULL only after the data migration (0003) backfills it.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
        ("kernel", "0008_service_supplier"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicecategory",
            name="tenant_id",
            field=models.UUIDField(db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="servicetype",
            name="tenant_id",
            field=models.UUIDField(db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="tenant_id",
            field=models.UUIDField(db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="orderstatushistory",
            name="tenant_id",
            field=models.UUIDField(db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="assigned_supplier",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_orders",
                to="kernel.servicesupplier",
            ),
        ),
    ]
