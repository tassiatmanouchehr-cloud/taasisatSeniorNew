"""
Sprint 3A refinement — ServiceSupplier.tenant_id becomes a real ForeignKey
to Tenant for referential integrity (was a raw UUIDField).

The physical column (kernel.service_supplier.tenant_id) and its existing
data are untouched — the FK's default db_column for a field named "tenant"
is "tenant_id", so no rename/rewrite is needed. Only the Django model state
changes (field renamed tenant_id -> tenant, now typed as ForeignKey) and a
FK constraint is added at the database level.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0008_service_supplier"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveIndex(model_name="servicesupplier", name="idx_supplier_tenant_type_st"),
                migrations.RemoveIndex(model_name="servicesupplier", name="idx_supplier_availability"),
                migrations.RemoveField(model_name="servicesupplier", name="tenant_id"),
                migrations.AddField(
                    model_name="servicesupplier",
                    name="tenant",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="service_suppliers",
                        to="kernel.tenant",
                    ),
                    preserve_default=False,
                ),
                migrations.AddIndex(
                    model_name="servicesupplier",
                    index=models.Index(
                        fields=["tenant", "supplier_type", "status"],
                        name="idx_supplier_tenant_type_st",
                    ),
                ),
                migrations.AddIndex(
                    model_name="servicesupplier",
                    index=models.Index(
                        fields=["tenant", "status", "availability_status"],
                        name="idx_supplier_availability",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "kernel"."service_supplier" '
                        'ADD CONSTRAINT "service_supplier_tenant_id_fkey" '
                        'FOREIGN KEY ("tenant_id") REFERENCES "kernel"."tenant" ("id");'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "kernel"."service_supplier" DROP CONSTRAINT "service_supplier_tenant_id_fkey";'
                    ),
                ),
            ],
        ),
    ]
