"""
Supplier Bridge — thin translator between accounts profiles and kernel's
generic Supplier Registry.

Kernel's ServiceSupplier (apps.kernel.models.supplier) and SupplierRegistry
(apps.kernel.services.supplier_registry) are domain-agnostic: they only know
about linked_entity_id/linked_entity_type. They must never import or
reference CaregiverProfile, OrganizationProfile, or any other accounts
concept directly.

This module is the ONLY place that translates between:
- apps.accounts profiles (CaregiverProfile, OrganizationProfile)
- apps.kernel.models.supplier.ServiceSupplier

Accounts must never create or query ServiceSupplier rows directly — every
lookup/creation goes through SupplierRegistry.

Per Sprint 3A: "Supplier registry must live in kernel and remain generic.
No caregiver-specific logic in kernel. Accounts may have a thin
translator/bridge only — accounts must never create ServiceSupplier
directly."
"""

from apps.kernel.models.supplier import ServiceSupplier, SupplierType
from apps.kernel.services.supplier_registry import SupplierRegistry

from ..models.profiles import CaregiverProfile, OrganizationProfile

CAREGIVER_LINKED_TYPE = "CaregiverProfile"
ORGANIZATION_LINKED_TYPE = "OrganizationProfile"


def get_or_create_supplier_for_caregiver(caregiver: CaregiverProfile, *, tenant_id=None) -> ServiceSupplier:
    """Translate a CaregiverProfile into its ServiceSupplier via the kernel registry."""
    resolved_tenant_id = tenant_id or caregiver.person.tenant_id
    return SupplierRegistry.get_or_create_supplier(
        tenant_id=resolved_tenant_id,
        linked_entity_id=caregiver.id,
        linked_entity_type=CAREGIVER_LINKED_TYPE,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        display_name=caregiver.display_name,
    )


def get_or_create_supplier_for_organization(organization: OrganizationProfile, *, tenant_id=None) -> ServiceSupplier:
    """Translate an OrganizationProfile into its ServiceSupplier via the kernel registry."""
    resolved_tenant_id = tenant_id or organization.tenant_id
    return SupplierRegistry.get_or_create_supplier(
        tenant_id=resolved_tenant_id,
        linked_entity_id=organization.id,
        linked_entity_type=ORGANIZATION_LINKED_TYPE,
        supplier_type=SupplierType.ORGANIZATION,
        display_name=organization.name,
    )


def resolve_supplier_entity(supplier: ServiceSupplier | None):
    """Resolve a ServiceSupplier back to its accounts-side profile instance, or None."""
    if supplier is None:
        return None
    if supplier.linked_entity_type == CAREGIVER_LINKED_TYPE:
        return CaregiverProfile.objects.filter(id=supplier.linked_entity_id).first()
    if supplier.linked_entity_type == ORGANIZATION_LINKED_TYPE:
        return OrganizationProfile.objects.filter(id=supplier.linked_entity_id).first()
    return None
