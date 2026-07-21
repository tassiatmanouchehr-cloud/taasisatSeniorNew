"""
Sprint 3A refinement — tenant_id becomes a real ForeignKey to Tenant on
ServiceCategory, ServiceType, Order, and OrderStatusHistory (was a raw
UUIDField), for referential integrity.

The physical tenant_id columns and their existing data are untouched — the
FK's default db_column for a field named "tenant" is "tenant_id", so no
rename/rewrite is needed. Only the Django model state changes (fields
renamed tenant_id -> tenant, now typed as ForeignKey) and FK constraints
are added at the database level. unique_together constraints already
reference the same physical columns, so they don't need to change either.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_enforce_tenant_and_remove_legacy"),
        ("kernel", "0008_service_supplier"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="servicecategory", name="tenant_id"),
                migrations.AddField(
                    model_name="servicecategory",
                    name="tenant",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="service_categories",
                        to="kernel.tenant",
                    ),
                    preserve_default=False,
                ),
                migrations.RemoveField(model_name="servicetype", name="tenant_id"),
                migrations.AddField(
                    model_name="servicetype",
                    name="tenant",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="service_types",
                        to="kernel.tenant",
                    ),
                    preserve_default=False,
                ),
                migrations.RemoveField(model_name="order", name="tenant_id"),
                migrations.AddField(
                    model_name="order",
                    name="tenant",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="kernel.tenant",
                    ),
                    preserve_default=False,
                ),
                migrations.RemoveField(model_name="orderstatushistory", name="tenant_id"),
                migrations.AddField(
                    model_name="orderstatushistory",
                    name="tenant",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_status_history",
                        to="kernel.tenant",
                    ),
                    preserve_default=False,
                ),
                migrations.AlterUniqueTogether(
                    name="servicecategory",
                    unique_together={("tenant", "slug")},
                ),
                migrations.AlterUniqueTogether(
                    name="servicetype",
                    unique_together={("tenant", "category", "slug")},
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "orders_service_category" '
                        'ADD CONSTRAINT "orders_service_category_tenant_id_fkey" '
                        'FOREIGN KEY ("tenant_id") REFERENCES "kernel"."tenant" ("id");'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "orders_service_category" '
                        'DROP CONSTRAINT "orders_service_category_tenant_id_fkey";'
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "orders_service_type" '
                        'ADD CONSTRAINT "orders_service_type_tenant_id_fkey" '
                        'FOREIGN KEY ("tenant_id") REFERENCES "kernel"."tenant" ("id");'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "orders_service_type" DROP CONSTRAINT "orders_service_type_tenant_id_fkey";'
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "orders_order" '
                        'ADD CONSTRAINT "orders_order_tenant_id_fkey" '
                        'FOREIGN KEY ("tenant_id") REFERENCES "kernel"."tenant" ("id");'
                    ),
                    reverse_sql=('ALTER TABLE "orders_order" DROP CONSTRAINT "orders_order_tenant_id_fkey";'),
                ),
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "orders_status_history" '
                        'ADD CONSTRAINT "orders_status_history_tenant_id_fkey" '
                        'FOREIGN KEY ("tenant_id") REFERENCES "kernel"."tenant" ("id");'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "orders_status_history" DROP CONSTRAINT "orders_status_history_tenant_id_fkey";'
                    ),
                ),
            ],
        ),
    ]
