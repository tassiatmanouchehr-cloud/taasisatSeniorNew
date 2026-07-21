"""
Management command: reconcile_organization_provider_suppliers — Epic 04
Sprint 3 (Enterprise Organization Isolation — Provider Affiliation
Activation).

apps.accounts.services.supplier_bridge.get_or_create_supplier_for_caregiver()
now creates an ORGANIZATION_PROVIDER-typed ServiceSupplier for a caregiver
whose provider_type is ORGANIZATION_AFFILIATED — but
SupplierRegistry.get_or_create_supplier()'s `defaults` only apply on first
creation, so a caregiver who was already affiliated before this change
keeps their existing INDEPENDENT_PROVIDER-typed row indefinitely unless
reconciled. This command does that one-time reconciliation, idempotently
(a caregiver already ORGANIZATION_PROVIDER-typed is a no-op).

Does not create any ServiceSupplier row — only updates the supplier_type
of a row that already exists, via
apps.kernel.services.supplier_registry.SupplierRegistry.set_supplier_type()
(the one place allowed to touch ServiceSupplier, same rule
supplier_bridge itself follows).

Usage:
    python manage.py reconcile_organization_provider_suppliers
    python manage.py reconcile_organization_provider_suppliers --dry-run
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Reconcile ServiceSupplier.supplier_type for already-affiliated caregivers (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would happen, write nothing.")

    def handle(self, *args, **options):
        from apps.accounts.models.profiles import CaregiverProfile, CaregiverProviderType
        from apps.accounts.services.supplier_bridge import CAREGIVER_LINKED_TYPE
        from apps.kernel.models.supplier import SupplierType
        from apps.kernel.services.supplier_registry import SupplierRegistry

        caregivers = CaregiverProfile.objects.filter(provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED)

        reconciled = 0
        already_correct = 0
        no_supplier_yet = 0

        for caregiver in caregivers:
            supplier = SupplierRegistry.find_by_linked_entity(
                linked_entity_id=caregiver.id,
                linked_entity_type=CAREGIVER_LINKED_TYPE,
            )
            if supplier is None:
                no_supplier_yet += 1
                continue
            if supplier.supplier_type == SupplierType.ORGANIZATION_PROVIDER:
                already_correct += 1
                continue

            if options["dry_run"]:
                self.stdout.write(
                    f"[dry-run] Would reconcile supplier {supplier.id} (caregiver {caregiver.id}): "
                    f"{supplier.supplier_type} -> {SupplierType.ORGANIZATION_PROVIDER}",
                )
                reconciled += 1
                continue

            SupplierRegistry.set_supplier_type(supplier, supplier_type=SupplierType.ORGANIZATION_PROVIDER)
            reconciled += 1

        verb = "Would reconcile" if options["dry_run"] else "Reconciled"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {reconciled}. Already correct: {already_correct}. No supplier yet: {no_supplier_yet}.",
            )
        )
