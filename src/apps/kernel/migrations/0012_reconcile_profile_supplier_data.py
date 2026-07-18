"""
Data migration: reconcile ACTIVE Profile <-> ACTIVE ServiceSupplier data
before the uniqueness constraint (next migration) can be safely applied.

Core Profile-ServiceSupplier Invariant Remediation, Phase 6. This is the
one-time counterpart to the idempotent
`reconcile_profile_supplier_invariant` management command — same rules,
but run automatically once as part of `migrate`, and implemented against
each app's *historical* migration-state models (`apps.get_model(...)`)
rather than the live model/service classes, per migration-safety
convention: a data migration must never import a live model class or
service, since either could evolve after this migration is written and
silently change what actually runs against production data.

Deliberately conservative: creates/repairs ONLY for `accounts.CaregiverProfile`
and `accounts.OrganizationProfile` rows whose `status` is already `"active"`
(ProfileStatus.ACTIVE's stored value) and are missing, or have a
non-`"active"`-status, `kernel.ServiceSupplier` row. Tenant is always
derived from the profile's own authoritative relation (`person.tenant_id`
for a caregiver, `tenant_id` directly for an organization) — never a
default/hinted tenant, so this can never cross a tenant boundary.

If any `(linked_entity_id, linked_entity_type)` pair already has more than
one `ServiceSupplier` row when this runs, there is no safe, deterministic
way to guess which one is the "real" survivor — this migration refuses to
guess and raises, aborting cleanly (this migration runs inside a single
DB transaction on PostgreSQL) so the operator can resolve the duplicate
by hand before re-running `migrate`. The same is true for a supplier row
whose `tenant_id` disagrees with its profile's own tenant.
"""

from django.db import migrations

CAREGIVER_LINKED_TYPE = "CaregiverProfile"
ORGANIZATION_LINKED_TYPE = "OrganizationProfile"
PROFILE_STATUS_ACTIVE = "active"
SUPPLIER_STATUS_ACTIVE = "active"
SUPPLIER_TYPE_INDEPENDENT_PROVIDER = "INDEPENDENT_PROVIDER"
SUPPLIER_TYPE_ORGANIZATION_PROVIDER = "ORGANIZATION_PROVIDER"
SUPPLIER_TYPE_ORGANIZATION = "ORGANIZATION"
CAREGIVER_PROVIDER_TYPE_ORGANIZATION_AFFILIATED = "organization_affiliated"


def _supplier_type_for_caregiver(caregiver) -> str:
    if caregiver.provider_type == CAREGIVER_PROVIDER_TYPE_ORGANIZATION_AFFILIATED:
        return SUPPLIER_TYPE_ORGANIZATION_PROVIDER
    return SUPPLIER_TYPE_INDEPENDENT_PROVIDER


def reconcile_forward(apps, schema_editor):
    CaregiverProfile = apps.get_model("accounts", "CaregiverProfile")
    OrganizationProfile = apps.get_model("accounts", "OrganizationProfile")
    ServiceSupplier = apps.get_model("kernel", "ServiceSupplier")

    def existing_suppliers(linked_entity_id, linked_entity_type):
        return list(
            ServiceSupplier.objects.filter(
                linked_entity_id=linked_entity_id, linked_entity_type=linked_entity_type,
            )
        )

    for caregiver in CaregiverProfile.objects.filter(status=PROFILE_STATUS_ACTIVE).select_related("person"):
        rows = existing_suppliers(caregiver.id, CAREGIVER_LINKED_TYPE)
        if len(rows) > 1:
            raise RuntimeError(
                f"reconcile_profile_supplier_data: {len(rows)} ServiceSupplier rows already exist for "
                f"CaregiverProfile {caregiver.id} — cannot safely pick a survivor automatically. "
                f"Resolve this duplicate by hand, then re-run migrate.",
            )

        tenant_id = caregiver.person.tenant_id
        if not rows:
            ServiceSupplier.objects.create(
                tenant_id=tenant_id,
                supplier_type=_supplier_type_for_caregiver(caregiver),
                linked_entity_id=caregiver.id,
                linked_entity_type=CAREGIVER_LINKED_TYPE,
                display_name=caregiver.display_name,
                status=SUPPLIER_STATUS_ACTIVE,
            )
            continue

        supplier = rows[0]
        if supplier.tenant_id != tenant_id:
            raise RuntimeError(
                f"reconcile_profile_supplier_data: ServiceSupplier {supplier.id} tenant={supplier.tenant_id} "
                f"disagrees with CaregiverProfile {caregiver.id} tenant={tenant_id} — refusing to guess which "
                f"is correct. Resolve this tenant mismatch by hand, then re-run migrate.",
            )
        if supplier.status != SUPPLIER_STATUS_ACTIVE:
            supplier.status = SUPPLIER_STATUS_ACTIVE
            supplier.save(update_fields=["status"])

    for organization in OrganizationProfile.objects.filter(status=PROFILE_STATUS_ACTIVE):
        rows = existing_suppliers(organization.id, ORGANIZATION_LINKED_TYPE)
        if len(rows) > 1:
            raise RuntimeError(
                f"reconcile_profile_supplier_data: {len(rows)} ServiceSupplier rows already exist for "
                f"OrganizationProfile {organization.id} — cannot safely pick a survivor automatically. "
                f"Resolve this duplicate by hand, then re-run migrate.",
            )

        tenant_id = organization.tenant_id
        if tenant_id is None:
            raise RuntimeError(
                f"reconcile_profile_supplier_data: OrganizationProfile {organization.id} is ACTIVE but has no "
                f"tenant — cannot derive an authoritative tenant to create/reconcile its ServiceSupplier. "
                f"Resolve this by hand, then re-run migrate.",
            )

        if not rows:
            ServiceSupplier.objects.create(
                tenant_id=tenant_id,
                supplier_type=SUPPLIER_TYPE_ORGANIZATION,
                linked_entity_id=organization.id,
                linked_entity_type=ORGANIZATION_LINKED_TYPE,
                display_name=organization.name,
                status=SUPPLIER_STATUS_ACTIVE,
            )
            continue

        supplier = rows[0]
        if supplier.tenant_id != tenant_id:
            raise RuntimeError(
                f"reconcile_profile_supplier_data: ServiceSupplier {supplier.id} tenant={supplier.tenant_id} "
                f"disagrees with OrganizationProfile {organization.id} tenant={tenant_id} — refusing to guess "
                f"which is correct. Resolve this tenant mismatch by hand, then re-run migrate.",
            )
        if supplier.status != SUPPLIER_STATUS_ACTIVE:
            supplier.status = SUPPLIER_STATUS_ACTIVE
            supplier.save(update_fields=["status"])


def reconcile_backward(apps, schema_editor):
    """Deliberately a no-op: reversing this migration would mean deleting
    or un-activating ServiceSupplier rows this migration created/fixed,
    which is indistinguishable from data a real activation legitimately
    created afterwards — there is no safe automatic reverse."""


class Migration(migrations.Migration):

    dependencies = [
        ("kernel", "0011_role_assignment_active_scope_constraint"),
        ("accounts", "0011_favorite"),
    ]

    operations = [
        migrations.RunPython(reconcile_forward, reconcile_backward),
    ]
