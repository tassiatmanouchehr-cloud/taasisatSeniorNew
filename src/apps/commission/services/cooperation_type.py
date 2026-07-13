"""
Cooperation-type constants shared by every commission service.

Not a Django model choice on any commission row itself — CooperationType is
a classification key used to select which PolicyDefinition/PolicyVersion
applies (see policy_service.py/resolver_service.py), and to select the
allocation shares carried inside a CommissionSnapshot.
"""

from django.db import models


class CooperationType(models.TextChoices):
    """How the assigned supplier relates to the platform for this order."""

    INDEPENDENT = "INDEPENDENT", "Independent Caregiver"
    AFFILIATED = "AFFILIATED", "Organization-Affiliated Caregiver"
    COMPANY_DIRECT = "COMPANY_DIRECT", "Organization as Direct Supplier"


def resolve_cooperation_type(*, supplier) -> str:
    """Maps an apps.kernel.models.supplier.ServiceSupplier to a CooperationType.

    Deliberately mirrors apps.finance.services.party_service
    .FinancialPartyService.resolve_party_for_supplier's own branching (the
    canonical place SupplierType is already interpreted for financial
    purposes) rather than inventing a second classification rule.
    """
    from apps.kernel.models.supplier import SupplierType

    if supplier.supplier_type == SupplierType.ORGANIZATION:
        return CooperationType.COMPANY_DIRECT
    if supplier.supplier_type == SupplierType.ORGANIZATION_PROVIDER:
        return CooperationType.AFFILIATED
    return CooperationType.INDEPENDENT
