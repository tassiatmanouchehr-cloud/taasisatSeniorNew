"""
Frozen dataclass DTOs — Module 12 foundation.

Mirrors the codebase's existing internal-DTO convention (there is no DRF
wiring anywhere in this project — see apps.matching.services.eligibility.
EligibilityResult and apps.kernel.events.base.DomainEvent, both frozen
dataclasses). SearchResultItem is a deliberately narrow, public-safe
projection of ServiceSupplier — it never exposes linked_entity_id,
financial_party_id, capabilities, or raw metadata.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class SearchQuery:
    """Normalized search input — see query_normalizer.normalize_query()."""

    tenant_id: uuid.UUID
    text: str = ""
    service_category_id: uuid.UUID | None = None
    supplier_type: str | None = None
    availability_status: str | None = None
    verification_level: str | None = None
    city: str | None = None
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class SearchResultItem:
    """Public-safe, ranked search result for one supplier."""

    supplier_id: uuid.UUID
    display_name: str
    supplier_type: str
    availability_status: str
    verification_level: str
    score: Decimal
    score_breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResultPage:
    """A bounded, paginated slice of ranked results."""

    items: tuple[SearchResultItem, ...]
    total_count: int
    limit: int
    offset: int
