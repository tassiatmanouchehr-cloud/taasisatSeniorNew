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

Epic 04 Sprint 3 (Enterprise Organization Isolation — Provider Affiliation
Activation): get_or_create_supplier_for_caregiver() now branches on
CaregiverProfile.provider_type, creating an ORGANIZATION_PROVIDER-typed
supplier for an organization-affiliated caregiver instead of always
INDEPENDENT_PROVIDER. This only affects NEWLY created ServiceSupplier rows
— SupplierRegistry.get_or_create_supplier()'s defaults only apply on
creation, so a caregiver who was already affiliated before this change
keeps their existing INDEPENDENT_PROVIDER-typed row until
apps.accounts.management.commands.reconcile_organization_provider_suppliers
is run. Financial policy is unchanged by this: apps.finance.services
.party_service.FinancialPartyService.resolve_party_for_supplier() still
keys strictly on supplier_type == SupplierType.ORGANIZATION (not
ORGANIZATION_PROVIDER), so an affiliated caregiver's earnings continue to
settle to their own FinancialParty/wallet, never the organization's — see
that service's own docstring, untouched by this Epic.
"""

from apps.kernel.models.supplier import ServiceSupplier, SupplierType
from apps.kernel.services.supplier_registry import SupplierRegistry

from ..models.profiles import CaregiverProfile, CaregiverProviderType, OrganizationProfile

CAREGIVER_LINKED_TYPE = "CaregiverProfile"
ORGANIZATION_LINKED_TYPE = "OrganizationProfile"


def _supplier_type_for_caregiver(caregiver: CaregiverProfile) -> str:
    if caregiver.provider_type == CaregiverProviderType.ORGANIZATION_AFFILIATED:
        return SupplierType.ORGANIZATION_PROVIDER
    return SupplierType.INDEPENDENT_PROVIDER


def get_or_create_supplier_for_caregiver(caregiver: CaregiverProfile, *, tenant_id=None) -> ServiceSupplier:
    """Translate a CaregiverProfile into its ServiceSupplier via the kernel registry."""
    resolved_tenant_id = tenant_id or caregiver.person.tenant_id
    return SupplierRegistry.get_or_create_supplier(
        tenant_id=resolved_tenant_id,
        linked_entity_id=caregiver.id,
        linked_entity_type=CAREGIVER_LINKED_TYPE,
        supplier_type=_supplier_type_for_caregiver(caregiver),
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


def resolve_organization_supplier_for_caregiver(
    caregiver_supplier: ServiceSupplier, *, tenant_id=None
) -> ServiceSupplier | None:
    """Financial Core PR-A: caregiver ServiceSupplier -> its active
    organization's own ServiceSupplier, or None. Kept here (not in
    apps.commission) because apps.accounts is this repository's only
    documented allowlisted bridge between accounts profiles
    (CaregiverProfile/OrganizationMembership/OrganizationProfile) and
    kernel.ServiceSupplier — see apps.kernel.tests.test_architecture_guardrails
    .ServiceSupplierProfileCouplingTest, and this module's own docstring
    ("Accounts must never create or query ServiceSupplier rows directly...
    every lookup/creation goes through SupplierRegistry" — the inverse
    direction, resolving supplier->accounts->supplier, belongs here too)."""
    from ..models.profiles import AffiliationStatus, OrganizationMembership

    caregiver_profile = resolve_supplier_entity(caregiver_supplier)
    if not isinstance(caregiver_profile, CaregiverProfile):
        return None

    membership = (
        OrganizationMembership.objects.filter(
            user_id=caregiver_profile.user_id,
            status=AffiliationStatus.APPROVED,
        )
        .select_related("organization")
        .first()
    )
    if membership is None:
        return None

    return get_or_create_supplier_for_organization(
        membership.organization,
        tenant_id=tenant_id or caregiver_supplier.tenant_id,
    )


def resolve_supplier_entities_bulk(suppliers) -> dict:
    """Bulk sibling of resolve_supplier_entity(): resolves many suppliers'
    CaregiverProfile/OrganizationProfile entities in at most two queries
    total (one per entity type) instead of one query per supplier.

    Added for Epic 06 (Marketplace Profiles & Discovery) Architecture
    Review remediation M1 — the public directory/home pages were issuing
    one CaregiverProfile query per candidate supplier, unbounded by the
    displayed page size. Returns {supplier.id: entity_or_None}.
    """
    suppliers = list(suppliers)
    caregiver_ids = {s.linked_entity_id for s in suppliers if s.linked_entity_type == CAREGIVER_LINKED_TYPE}
    organization_ids = {s.linked_entity_id for s in suppliers if s.linked_entity_type == ORGANIZATION_LINKED_TYPE}

    caregivers_by_id = {}
    if caregiver_ids:
        caregivers_by_id = {c.id: c for c in CaregiverProfile.objects.filter(id__in=caregiver_ids)}

    organizations_by_id = {}
    if organization_ids:
        organizations_by_id = {o.id: o for o in OrganizationProfile.objects.filter(id__in=organization_ids)}

    resolved = {}
    for supplier in suppliers:
        if supplier.linked_entity_type == CAREGIVER_LINKED_TYPE:
            resolved[supplier.id] = caregivers_by_id.get(supplier.linked_entity_id)
        elif supplier.linked_entity_type == ORGANIZATION_LINKED_TYPE:
            resolved[supplier.id] = organizations_by_id.get(supplier.linked_entity_id)
        else:
            resolved[supplier.id] = None
    return resolved
