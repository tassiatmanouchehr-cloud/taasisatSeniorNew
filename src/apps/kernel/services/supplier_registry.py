"""
Supplier Registry — kernel-owned service that is the single source of truth
for ServiceSupplier creation and lookup.

This is the ONLY code path allowed to create or fetch ServiceSupplier rows.
It is deliberately generic: every argument is an opaque identifier or a
plain string. This module must NEVER import or reference a vertical
concept (CaregiverProfile, OrganizationProfile, "senior care", or any
other business/accounts model).

Vertical apps do not call ServiceSupplier.objects directly — they go
through a thin per-app bridge (e.g. apps.accounts.services.supplier_bridge)
that translates their own models into the generic terms this registry
expects, and then calls this registry.

Per Sprint 3A: "Supplier registry must live in kernel and remain generic.
No caregiver-specific logic in kernel. Accounts may have a thin
translator/bridge only — accounts must never create ServiceSupplier
directly."
"""

import uuid

from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus


class SupplierRegistry:
    """Central, generic registry for ServiceSupplier creation and lookup."""

    @classmethod
    def get_or_create_supplier(
        cls,
        *,
        tenant_id: uuid.UUID,
        linked_entity_id: uuid.UUID,
        linked_entity_type: str,
        supplier_type: str,
        display_name: str,
        status: str = SupplierStatus.ACTIVE,
    ) -> ServiceSupplier:
        """
        Get or create the ServiceSupplier for a given (linked_entity_id,
        linked_entity_type) pair. This is the only place a ServiceSupplier
        row may be created.
        """
        supplier, _ = ServiceSupplier.objects.get_or_create(
            linked_entity_id=linked_entity_id,
            linked_entity_type=linked_entity_type,
            defaults={
                "tenant_id": tenant_id,
                "supplier_type": supplier_type,
                "display_name": display_name,
                "status": status,
            },
        )
        return supplier

    @classmethod
    def resolve_by_id(cls, supplier_id: uuid.UUID, *, tenant_id: uuid.UUID) -> ServiceSupplier:
        """
        Resolve a specific supplier by id within a tenant.

        Raises:
            ServiceSupplier.DoesNotExist: If not found or wrong tenant.
        """
        return ServiceSupplier.objects.get(id=supplier_id, tenant_id=tenant_id)

    @classmethod
    def find_by_linked_entity(cls, *, linked_entity_id: uuid.UUID, linked_entity_type: str) -> ServiceSupplier | None:
        """Look up an existing supplier by its linked entity, without creating one."""
        return ServiceSupplier.objects.filter(
            linked_entity_id=linked_entity_id,
            linked_entity_type=linked_entity_type,
        ).first()

    @classmethod
    def set_supplier_type(cls, supplier: ServiceSupplier, *, supplier_type: str) -> ServiceSupplier:
        """
        Reconcile an existing supplier's type in place — the generic
        counterpart to get_or_create_supplier()'s "create with this type"
        (whose `defaults` never apply to an already-existing row). A
        no-op if the supplier already has the requested type.

        Generic by the same rule as the rest of this module: this method
        knows nothing about *why* a caller wants a type change (Epic 04's
        organization-affiliation reconciliation is one reason; it is not
        the only one this method need ever serve).
        """
        if supplier.supplier_type == supplier_type:
            return supplier
        supplier.supplier_type = supplier_type
        supplier.save(update_fields=["supplier_type", "updated_at", "version"])
        return supplier

    @classmethod
    def set_service_categories(cls, supplier: ServiceSupplier, *, service_category_ids: list[str]) -> ServiceSupplier:
        """Reconcile an existing supplier's offered service categories in
        place — generic by the same rule as set_supplier_type() (this
        method knows nothing about *why* a caller wants the list changed;
        Epic 06 Sprint 2's provider self-profile editing is one reason,
        it is not the only one this method need ever serve)."""
        supplier.service_categories = list(service_category_ids)
        supplier.save(update_fields=["service_categories", "updated_at", "version"])
        return supplier
