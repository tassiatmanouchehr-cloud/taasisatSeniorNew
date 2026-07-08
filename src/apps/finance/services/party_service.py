"""
FinancialPartyService — Module 05 foundation.

Resolves the FinancialParty behind an operational entity (ServiceSupplier,
CustomerProfile, Tenant). This is the only code that creates FinancialParty
rows. Kept generic: no vertical-specific (e.g. elder-care) logic — only the
platform-generic entities already owned by kernel/accounts.
"""

import logging

from django.db import transaction

from apps.kernel.models.supplier import ServiceSupplier, SupplierType
from apps.kernel.models.tenant import Tenant
from apps.kernel.services.event_publisher import EventPublisher

from ..models import FinancialParty, FinancialPartyType
from .errors import FinanceError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class FinancialPartyService:
    """Resolves (get-or-create) the FinancialParty for an operational entity."""

    @classmethod
    @transaction.atomic
    def resolve_party_for_supplier(cls, service_supplier: ServiceSupplier) -> FinancialParty:
        party_type = (
            FinancialPartyType.ORGANIZATION
            if service_supplier.supplier_type == SupplierType.ORGANIZATION
            else FinancialPartyType.SUPPLIER
        )
        return cls._resolve(
            tenant_id=service_supplier.tenant_id,
            linked_entity_type="ServiceSupplier",
            linked_entity_id=service_supplier.id,
            party_type=party_type,
            display_name=service_supplier.display_name,
        )

    @classmethod
    @transaction.atomic
    def resolve_party_for_customer(cls, customer_profile) -> FinancialParty:
        tenant_id = customer_profile.person.tenant_id
        return cls._resolve(
            tenant_id=tenant_id,
            linked_entity_type="CustomerProfile",
            linked_entity_id=customer_profile.id,
            party_type=FinancialPartyType.CUSTOMER,
            display_name=customer_profile.display_name,
        )

    @classmethod
    @transaction.atomic
    def resolve_platform_party(cls, tenant: Tenant) -> FinancialParty:
        return cls._resolve(
            tenant_id=tenant.id,
            linked_entity_type="Tenant",
            linked_entity_id=tenant.id,
            party_type=FinancialPartyType.PLATFORM,
            display_name=tenant.name,
        )

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _resolve(cls, *, tenant_id, linked_entity_type, linked_entity_id, party_type, display_name) -> FinancialParty:
        if not tenant_id:
            raise FinanceError("Cannot resolve a FinancialParty without a tenant_id.")

        party, created = FinancialParty.objects.get_or_create(
            tenant_id=tenant_id,
            linked_entity_type=linked_entity_type,
            linked_entity_id=linked_entity_id,
            party_type=party_type,
            defaults={"display_name": display_name},
        )

        if not created and party.display_name != display_name:
            party.display_name = display_name
            party.save(update_fields=["display_name", "updated_at"])

        EventPublisher.publish(
            tenant_id=tenant_id,
            event_type="Finance.Party.Resolved.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=party.id,
            source_entity_type="FinancialParty",
            payload={
                "linked_entity_type": linked_entity_type,
                "linked_entity_id": str(linked_entity_id),
                "party_type": party_type,
                "created": created,
            },
        )

        return party
