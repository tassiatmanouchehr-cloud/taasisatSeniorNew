"""
Sprint 3A — Schema step 3/3: now that tenant_id is fully backfilled (0003),
enforce it as NOT NULL and make catalog uniqueness tenant-scoped instead of
global. Also drop the legacy assigned_provider / assigned_organization
fields on Order now that assigned_supplier (ServiceSupplier) is the single
source of truth for assignment.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_backfill_tenant_and_supplier_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicecategory",
            name="tenant_id",
            field=models.UUIDField(db_index=True),
        ),
        migrations.AlterField(
            model_name="servicetype",
            name="tenant_id",
            field=models.UUIDField(db_index=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="tenant_id",
            field=models.UUIDField(db_index=True),
        ),
        migrations.AlterField(
            model_name="orderstatushistory",
            name="tenant_id",
            field=models.UUIDField(db_index=True),
        ),
        migrations.AlterField(
            model_name="servicecategory",
            name="slug",
            field=models.SlugField(max_length=100),
        ),
        migrations.AlterUniqueTogether(
            name="servicecategory",
            unique_together={("tenant_id", "slug")},
        ),
        migrations.AlterUniqueTogether(
            name="servicetype",
            unique_together={("tenant_id", "category", "slug")},
        ),
        migrations.RemoveField(
            model_name="order",
            name="assigned_provider",
        ),
        migrations.RemoveField(
            model_name="order",
            name="assigned_organization",
        ),
    ]
