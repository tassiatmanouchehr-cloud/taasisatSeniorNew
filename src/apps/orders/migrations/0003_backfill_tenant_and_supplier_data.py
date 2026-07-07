"""
Sprint 3A — Data step 2/3.

- Backfills tenant_id on ServiceCategory, ServiceType, and Order to the
  platform default tenant (slug="salmandyar"), matching
  apps.kernel.services.tenant_service.TenantService.get_default_tenant().
- Backfills OrderStatusHistory.tenant_id from its parent Order.
- Backfills Order.assigned_supplier from the legacy assigned_provider /
  assigned_organization fields (still present at this point — they are
  only removed in the following schema migration), creating a
  ServiceSupplier per distinct caregiver/organization as needed.

This must run before 0004 makes tenant_id NOT NULL and drops the legacy
assignment fields.
"""

from django.db import migrations

DEFAULT_TENANT_SLUG = "salmandyar"
DEFAULT_TENANT_NAME = "سالمندیار"


def backfill(apps, schema_editor):
    Tenant = apps.get_model("kernel", "Tenant")
    ServiceSupplier = apps.get_model("kernel", "ServiceSupplier")
    ServiceCategory = apps.get_model("orders", "ServiceCategory")
    ServiceType = apps.get_model("orders", "ServiceType")
    Order = apps.get_model("orders", "Order")
    OrderStatusHistory = apps.get_model("orders", "OrderStatusHistory")
    CaregiverProfile = apps.get_model("accounts", "CaregiverProfile")
    OrganizationProfile = apps.get_model("accounts", "OrganizationProfile")

    tenant, _ = Tenant.objects.get_or_create(
        slug=DEFAULT_TENANT_SLUG,
        defaults={"name": DEFAULT_TENANT_NAME, "status": "active"},
    )

    ServiceCategory.objects.filter(tenant_id__isnull=True).update(tenant_id=tenant.id)
    ServiceType.objects.filter(tenant_id__isnull=True).update(tenant_id=tenant.id)
    Order.objects.filter(tenant_id__isnull=True).update(tenant_id=tenant.id)

    # Backfill assigned_supplier from the legacy CaregiverProfile assignment.
    for order in Order.objects.filter(
        assigned_supplier__isnull=True, assigned_provider__isnull=False
    ).iterator():
        caregiver = CaregiverProfile.objects.filter(id=order.assigned_provider_id).first()
        if not caregiver:
            continue
        supplier, _ = ServiceSupplier.objects.get_or_create(
            linked_entity_id=caregiver.id,
            linked_entity_type="CaregiverProfile",
            defaults={
                "tenant_id": order.tenant_id,
                "supplier_type": "INDEPENDENT_PROVIDER",
                "display_name": caregiver.display_name,
                "status": "active",
            },
        )
        order.assigned_supplier_id = supplier.id
        order.save(update_fields=["assigned_supplier"])

    # Backfill assigned_supplier from the legacy OrganizationProfile assignment.
    for order in Order.objects.filter(
        assigned_supplier__isnull=True, assigned_organization__isnull=False
    ).iterator():
        organization = OrganizationProfile.objects.filter(id=order.assigned_organization_id).first()
        if not organization:
            continue
        supplier, _ = ServiceSupplier.objects.get_or_create(
            linked_entity_id=organization.id,
            linked_entity_type="OrganizationProfile",
            defaults={
                "tenant_id": order.tenant_id,
                "supplier_type": "ORGANIZATION",
                "display_name": organization.name,
                "status": "active",
            },
        )
        order.assigned_supplier_id = supplier.id
        order.save(update_fields=["assigned_supplier"])

    # OrderStatusHistory tenant_id is denormalized from its Order.
    for row in OrderStatusHistory.objects.filter(tenant_id__isnull=True).select_related("order").iterator():
        row.tenant_id = row.order.tenant_id
        row.save(update_fields=["tenant_id"])


def noop_reverse(apps, schema_editor):
    """Backfilled data is not removed on reverse — schema rollback (0002) leaves fields nullable."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_add_tenant_and_supplier_fields"),
        ("accounts", "0002_profiles_v2"),
        ("kernel", "0008_service_supplier"),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
