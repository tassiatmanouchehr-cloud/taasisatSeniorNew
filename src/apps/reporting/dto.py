"""
Reporting DTOs — Module 16 foundation.

Frozen dataclasses only, mirroring the DTO convention established by
apps.matching.services.eligibility.EligibilityResult /
apps.kernel.events.base.DomainEvent. No ORM objects are ever returned by a
reporting service — callers only ever see these.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class OrderCountsReport:
    tenant_id: uuid.UUID
    total_orders: int
    active_orders: int
    completed_orders: int
    cancelled_orders: int
    by_status: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderPerformanceReport:
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    completed_services: int
    reputation_average: Decimal | None
    reputation_review_count: int
    availability_status: str
    total_assignments: int
    active_assignments: int


@dataclass(frozen=True)
class FinancialSummaryReport:
    tenant_id: uuid.UUID
    invoices_issued_count: int
    invoices_issued_total: Decimal
    payments_succeeded_count: int
    payments_succeeded_total: Decimal
    wallet_total_balance: Decimal
    wallet_transaction_count: int
    wallet_transaction_total: Decimal


@dataclass(frozen=True)
class MarketplaceStatsReport:
    tenant_id: uuid.UUID
    supplier_count: int
    organization_count: int
    customer_count: int
    supplier_type_distribution: dict[str, int] = field(default_factory=dict)
    category_distribution: dict[str, int] = field(default_factory=dict)
