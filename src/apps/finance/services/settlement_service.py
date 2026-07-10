"""
SettlementService — Module 05 settlement/netting foundation.

Calculates each FinancialParty's net position from RESOLVED obligations
and materializes it as a SettlementBatch + SettlementItem rows. No real
payout/bank transfer happens here.
"""

import logging
from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from apps.kernel.services.event_publisher import EventPublisher
from apps.kernel.services.permission_service import PermissionService

from ..models import (
    DEFAULT_CURRENCY,
    FinancialObligation,
    ObligationStatus,
    SettlementBatch,
    SettlementBatchStatus,
    SettlementItem,
    SettlementItemStatus,
)
from ..permission_keys import FINANCE_SETTLEMENT_CREATE_BATCH

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class SettlementService:
    """Calculates net positions and materializes SettlementBatch/SettlementItem rows."""

    @classmethod
    def calculate_net_position(cls, *, tenant_id, period_start=None, period_end=None) -> dict:
        """Returns {party_id (uuid): Decimal net amount}. Positive = party is owed money."""
        obligations = FinancialObligation.objects.filter(
            tenant_id=tenant_id, status=ObligationStatus.RESOLVED,
        )
        if period_start:
            obligations = obligations.filter(resolved_at__gte=period_start)
        if period_end:
            obligations = obligations.filter(resolved_at__lte=period_end)

        net_positions: dict = defaultdict(lambda: Decimal("0"))
        for obligation in obligations:
            net_positions[obligation.creditor_party_id] += obligation.amount
            net_positions[obligation.debtor_party_id] -= obligation.amount

        return dict(net_positions)

    @classmethod
    @transaction.atomic
    def create_batch(cls, *, tenant_id, currency=None, period_start=None, period_end=None, actor=None) -> SettlementBatch:
        PermissionService.require(actor, FINANCE_SETTLEMENT_CREATE_BATCH, tenant_id=tenant_id)

        net_positions = cls.calculate_net_position(
            tenant_id=tenant_id, period_start=period_start, period_end=period_end,
        )
        resolved_currency = currency or DEFAULT_CURRENCY

        batch = SettlementBatch.objects.create(
            tenant_id=tenant_id,
            status=SettlementBatchStatus.CALCULATED,
            currency=resolved_currency,
            period_start=period_start,
            period_end=period_end,
        )

        items = [
            SettlementItem(
                tenant_id=tenant_id,
                batch=batch,
                party_id=party_id,
                amount=amount,
                currency=resolved_currency,
                status=SettlementItemStatus.PENDING,
            )
            for party_id, amount in net_positions.items()
            if amount != 0
        ]
        SettlementItem.objects.bulk_create(items)

        batch.total_amount = sum((abs(item.amount) for item in items), Decimal("0"))
        batch.save(update_fields=["total_amount"])

        EventPublisher.publish(
            tenant_id=tenant_id,
            event_type="Finance.Settlement.BatchCreated.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=batch.id,
            source_entity_type="SettlementBatch",
            payload={
                "item_count": len(items),
                "total_amount": str(batch.total_amount),
                "currency": resolved_currency,
            },
        )

        return batch
