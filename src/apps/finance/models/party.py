"""
FinancialParty — Module 05 foundation.

Operational roles (Customer, ServiceSupplier, Organization, Platform) are
not always the same as the financial counterparty. FinancialParty is the
generic identity that ledger entries, obligations, payments, wallets, and
escrow records point to — never a raw user/profile id directly.

See apps.finance.services.party_service.FinancialPartyService for
resolution helpers (the only code that should create these records).
"""

import uuid

from django.db import models

from apps.common.enums import EntityStatus
from apps.common.managers import TenantScopedManager


class FinancialPartyType(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Customer"
    SUPPLIER = "SUPPLIER", "Supplier"
    PLATFORM = "PLATFORM", "Platform"
    ORGANIZATION = "ORGANIZATION", "Organization"


class FinancialParty(models.Model):
    """Generic financial counterparty identity, decoupled from operational entities."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="financial_parties",
    )

    linked_entity_type = models.CharField(
        max_length=100,
        help_text="Type of the linked operational entity, e.g. 'ServiceSupplier', 'CustomerProfile', 'Tenant'.",
    )
    linked_entity_id = models.UUIDField(
        help_text="ID of the linked operational entity.",
    )

    party_type = models.CharField(max_length=20, choices=FinancialPartyType.choices, db_index=True)
    display_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=EntityStatus.choices, default=EntityStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_financial_party"
        ordering = ["display_name"]
        unique_together = [("tenant", "linked_entity_type", "linked_entity_id", "party_type")]
        indexes = [
            models.Index(fields=["tenant", "party_type", "status"], name="idx_finparty_tenant_type_st"),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.party_type})"
