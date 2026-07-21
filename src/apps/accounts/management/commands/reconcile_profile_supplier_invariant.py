"""
Management command: reconcile_profile_supplier_invariant — Core
Profile-ServiceSupplier Invariant Remediation.

Idempotent, tenant-safe, dry-run-capable reconciliation of the activation
invariant `ProfileActivationService` now enforces going forward for every
*new* activation: an ACTIVE `CaregiverProfile`/`OrganizationProfile` must
be backed by a `ServiceSupplier` that is itself ACTIVE. This command
repairs profiles that reached ACTIVE before that enforcement existed (or
whose supplier drifted out of sync some other way), using exactly the
same sanctioned path activation itself uses —
`apps.accounts.services.supplier_bridge.sync_supplier_for_profile_activation()`
— never `ServiceSupplier.objects` directly.

Safe, auto-repaired (each in its own transaction, one per profile — a
failure on one profile never rolls back an earlier repair):
  - ACTIVE profile with no supplier at all               -> created
  - ACTIVE profile whose supplier exists but is not
    itself ACTIVE                                        -> reconciled
  - ACTIVE profile whose supplier already matches         -> already_correct

`supplier_type` *repair* (e.g. INDEPENDENT_PROVIDER vs
ORGANIZATION_PROVIDER for an organization-affiliated caregiver) is a
separate, already-existing concern —
`apps.accounts.management.commands.reconcile_organization_provider_suppliers`
owns fixing it — and this command never writes `supplier_type`. It does,
however, still *detect and report* a supplier_type mismatch (independent
pre-merge review of PR #18, Required Fix 7: an operator running only this
command must not be left with zero visibility into type drift) under
"invalid", with an explicit message naming
`reconcile_organization_provider_suppliers` as the command that repairs it.

Detected and reported only — never auto-repaired, because no
unambiguous, repository-backed survivor/cleanup rule exists for these
(a wrong guess could cross a tenant boundary or destroy history):
  - duplicate (linked_entity_id, linked_entity_type) pairs
  - suppliers whose linked_entity_id resolves to no profile (orphans)
  - suppliers whose tenant_id disagrees with their profile's own tenant
  - a non-ACTIVE profile that already has an ACTIVE supplier (the
    reverse of this command's own invariant — repairing it would mean
    suspending/deactivating a supplier, which is BG-019 lifecycle-service
    territory, explicitly out of scope for this remediation)
  - malformed/unsupported linked_entity_type values
All of the above are reported under "invalid".

A per-profile exception during an otherwise-eligible repair is caught,
rolled back for that profile only, and reported under "failed" — it
never aborts the run for the remaining profiles.

Usage:
    python manage.py reconcile_profile_supplier_invariant
    python manage.py reconcile_profile_supplier_invariant --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Reconcile the ACTIVE-profile <-> ACTIVE-ServiceSupplier invariant (idempotent, dry-run capable). "
        "Detects (never repairs) supplier_type mismatches too — reconciled by "
        "'manage.py reconcile_organization_provider_suppliers'."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would happen, write nothing.")

    def handle(self, *args, **options):
        from apps.accounts.models.profiles import (
            CaregiverProfile,
            CaregiverProviderType,
            OrganizationProfile,
            ProfileStatus,
        )
        from apps.accounts.services.supplier_bridge import (
            CAREGIVER_LINKED_TYPE,
            ORGANIZATION_LINKED_TYPE,
            sync_supplier_for_profile_activation,
        )
        from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
        from apps.kernel.services.supplier_registry import SupplierRegistry

        dry_run = options["dry_run"]
        counts = {"created": 0, "reconciled": 0, "already_correct": 0, "skipped": 0, "invalid": 0, "failed": 0}
        invalid_details: list[str] = []

        def _tenant_id_for(profile) -> object:
            if isinstance(profile, CaregiverProfile):
                return profile.person.tenant_id
            return profile.tenant_id

        def _linked_type_for(profile) -> str:
            return CAREGIVER_LINKED_TYPE if isinstance(profile, CaregiverProfile) else ORGANIZATION_LINKED_TYPE

        def _expected_supplier_type_for(profile) -> str:
            if isinstance(profile, CaregiverProfile):
                if profile.provider_type == CaregiverProviderType.ORGANIZATION_AFFILIATED:
                    return SupplierType.ORGANIZATION_PROVIDER
                return SupplierType.INDEPENDENT_PROVIDER
            return SupplierType.ORGANIZATION

        def _report_type_mismatch_if_any(*, profile, linked_type, supplier) -> None:
            """Detection only — supplier_type repair is owned by
            reconcile_organization_provider_suppliers, never written here."""
            expected = _expected_supplier_type_for(profile)
            if supplier.supplier_type == expected:
                return
            counts["invalid"] += 1
            invalid_details.append(
                f"SUPPLIER_TYPE MISMATCH: supplier {supplier.id} ({linked_type} {profile.id}) has "
                f"supplier_type={supplier.supplier_type}, expected {expected} — not repaired by this command; "
                f"run 'manage.py reconcile_organization_provider_suppliers' to reconcile supplier_type.",
            )

        def _process_active_profile(profile):
            linked_type = _linked_type_for(profile)
            profile_tenant_id = _tenant_id_for(profile)
            supplier = SupplierRegistry.find_by_linked_entity(
                linked_entity_id=profile.id,
                linked_entity_type=linked_type,
            )

            if supplier is None:
                if dry_run:
                    self.stdout.write(f"[dry-run] Would create supplier for {linked_type} {profile.id}")
                    counts["created"] += 1
                    return
                try:
                    with transaction.atomic():
                        sync_supplier_for_profile_activation(profile, tenant_id=profile_tenant_id)
                    counts["created"] += 1
                except Exception as exc:  # noqa: BLE001 - reported per-row, loop must continue
                    counts["failed"] += 1
                    invalid_details.append(f"FAILED creating supplier for {linked_type} {profile.id}: {exc}")
                return

            if supplier.tenant_id != profile_tenant_id:
                counts["invalid"] += 1
                invalid_details.append(
                    f"TENANT MISMATCH: supplier {supplier.id} tenant={supplier.tenant_id} "
                    f"!= {linked_type} {profile.id} tenant={profile_tenant_id} — skipped, not auto-repaired.",
                )
                return

            _report_type_mismatch_if_any(profile=profile, linked_type=linked_type, supplier=supplier)

            if supplier.status == SupplierStatus.ACTIVE:
                counts["already_correct"] += 1
                return

            if dry_run:
                self.stdout.write(
                    f"[dry-run] Would reconcile supplier {supplier.id} ({linked_type} {profile.id}): "
                    f"status {supplier.status} -> {SupplierStatus.ACTIVE}",
                )
                counts["reconciled"] += 1
                return

            try:
                with transaction.atomic():
                    sync_supplier_for_profile_activation(profile, tenant_id=profile_tenant_id)
                counts["reconciled"] += 1
            except Exception as exc:  # noqa: BLE001 - reported per-row, loop must continue
                counts["failed"] += 1
                invalid_details.append(f"FAILED reconciling supplier {supplier.id} ({linked_type} {profile.id}): {exc}")

        # 1. Walk every ACTIVE profile — the only case this command may write to.
        for caregiver in CaregiverProfile.objects.filter(status=ProfileStatus.ACTIVE).select_related("person"):
            _process_active_profile(caregiver)
        for organization in OrganizationProfile.objects.filter(status=ProfileStatus.ACTIVE):
            _process_active_profile(organization)

        # 2. Non-ACTIVE profiles that already carry an ACTIVE supplier — detect only.
        for caregiver in CaregiverProfile.objects.exclude(status=ProfileStatus.ACTIVE).select_related("person"):
            supplier = SupplierRegistry.find_by_linked_entity(
                linked_entity_id=caregiver.id,
                linked_entity_type=CAREGIVER_LINKED_TYPE,
            )
            if supplier is None:
                counts["skipped"] += 1
            elif supplier.status == SupplierStatus.ACTIVE:
                counts["invalid"] += 1
                invalid_details.append(
                    f"NON-ACTIVE PROFILE WITH ACTIVE SUPPLIER: caregiver {caregiver.id} "
                    f"(status={caregiver.status}) has ACTIVE supplier {supplier.id} — skipped, not auto-repaired.",
                )
            else:
                counts["skipped"] += 1
        for organization in OrganizationProfile.objects.exclude(status=ProfileStatus.ACTIVE):
            supplier = SupplierRegistry.find_by_linked_entity(
                linked_entity_id=organization.id,
                linked_entity_type=ORGANIZATION_LINKED_TYPE,
            )
            if supplier is None:
                counts["skipped"] += 1
            elif supplier.status == SupplierStatus.ACTIVE:
                counts["invalid"] += 1
                invalid_details.append(
                    f"NON-ACTIVE PROFILE WITH ACTIVE SUPPLIER: organization {organization.id} "
                    f"(status={organization.status}) has ACTIVE supplier {supplier.id} — skipped, not auto-repaired.",
                )
            else:
                counts["skipped"] += 1

        # 3. Duplicate identity pairs, orphans, malformed types — whole-table checks, detect only.
        valid_types = {CAREGIVER_LINKED_TYPE, ORGANIZATION_LINKED_TYPE}
        caregiver_ids = set(CaregiverProfile.objects.values_list("id", flat=True))
        organization_ids = set(OrganizationProfile.objects.values_list("id", flat=True))

        from django.db.models import Count

        duplicate_pairs = (
            ServiceSupplier.objects.values("linked_entity_id", "linked_entity_type")
            .annotate(row_count=Count("id"))
            .filter(row_count__gt=1)
        )
        for pair in duplicate_pairs:
            counts["invalid"] += 1
            invalid_details.append(
                f"DUPLICATE IDENTITY PAIR: linked_entity_id={pair['linked_entity_id']} "
                f"linked_entity_type={pair['linked_entity_type']} has {pair['row_count']} ServiceSupplier rows "
                f"— skipped, no deterministic survivor rule established.",
            )

        for supplier in ServiceSupplier.objects.all():
            if supplier.linked_entity_type not in valid_types:
                counts["invalid"] += 1
                invalid_details.append(
                    f"MALFORMED linked_entity_type={supplier.linked_entity_type!r} on supplier {supplier.id}",
                )
            elif (
                supplier.linked_entity_type == CAREGIVER_LINKED_TYPE and supplier.linked_entity_id not in caregiver_ids
            ):
                counts["invalid"] += 1
                invalid_details.append(
                    f"ORPHAN supplier {supplier.id}: no CaregiverProfile {supplier.linked_entity_id}"
                )
            elif (
                supplier.linked_entity_type == ORGANIZATION_LINKED_TYPE
                and supplier.linked_entity_id not in organization_ids
            ):
                counts["invalid"] += 1
                invalid_details.append(
                    f"ORPHAN supplier {supplier.id}: no OrganizationProfile {supplier.linked_entity_id}"
                )

        for line in invalid_details:
            self.stdout.write(self.style.WARNING(line))

        verb = "Would repair" if dry_run else "Repaired"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: created={counts['created']} reconciled={counts['reconciled']} "
                f"already_correct={counts['already_correct']} skipped={counts['skipped']} "
                f"invalid={counts['invalid']} failed={counts['failed']}",
            )
        )
