"""
DiscoveryRankingService — Module 12 foundation.

Deterministic, explainable weighted ranking. Every candidate gets a
score_breakdown showing exactly which signal contributed what — no opaque
scoring, no ML.

Price-competitiveness is intentionally NOT a signal here:
apps.pricing.services.QuoteService.generate_quote() always persists a
Quote + QuoteLine rows (there is no side-effect-free calculation path),
and a read-only search must never write data. This is deferred until
Pricing exposes a non-persistent calculation method.
"""

from decimal import Decimal

from apps.kernel.models.supplier import AvailabilityStatus, ServiceSupplier, VerificationLevel

from .configuration import DiscoveryConfiguration
from .dto import SearchResultItem

_VERIFICATION_TIER = {
    VerificationLevel.UNVERIFIED: Decimal("0"),
    VerificationLevel.BASIC: Decimal("1"),
    VerificationLevel.ADVANCED: Decimal("2"),
    VerificationLevel.PREMIUM: Decimal("3"),
}


class DiscoveryRankingService:
    """Scores and deterministically orders a list of ServiceSupplier candidates."""

    @classmethod
    def rank(cls, *, tenant_id, suppliers: list[ServiceSupplier]) -> list[SearchResultItem]:
        weights = DiscoveryConfiguration.get_ranking_weights(tenant_id=tenant_id)
        capacity_exceeded_by_id = cls._bulk_capacity_exceeded(suppliers)
        scored = [cls._score(supplier, weights, capacity_exceeded_by_id) for supplier in suppliers]
        scored.sort(key=lambda item: (-item.score, str(item.supplier_id)))
        return scored

    @staticmethod
    def _bulk_capacity_exceeded(suppliers: list[ServiceSupplier]) -> dict:
        """Batched counterpart of CapacityService.is_capacity_exceeded(),
        computed once per rank() call in a fixed, small number of queries
        regardless of candidate count — see
        CapacityService.bulk_is_capacity_exceeded()'s own docstring. This
        replaces the previous per-candidate CapacityService.is_capacity_
        exceeded() call inside _score()/_capacity_bonus(), which issued
        one (or two) queries per supplier and was this repository's
        recorded KL-012 N+1. The capacity rule itself — no active
        CapacityRule means uncapped — is unchanged."""
        from apps.availability.services import CapacityService

        return CapacityService.bulk_is_capacity_exceeded(supplier_ids=[supplier.id for supplier in suppliers])

    @classmethod
    def _score(
        cls,
        supplier: ServiceSupplier,
        weights: dict[str, Decimal],
        capacity_exceeded_by_id: dict,
    ) -> SearchResultItem:
        verification_component = (
            _VERIFICATION_TIER.get(supplier.verification_level, Decimal("0")) * weights["verification"]
        )
        reputation_component = (supplier.reputation_score or Decimal("0")) * weights["reputation"]
        availability_component = cls._availability_bonus(supplier) * weights["availability"]
        capacity_component = cls._capacity_bonus(supplier, capacity_exceeded_by_id) * weights["capacity"]

        total_score = verification_component + reputation_component + availability_component + capacity_component

        return SearchResultItem(
            supplier_id=supplier.id,
            display_name=supplier.display_name,
            supplier_type=supplier.supplier_type,
            availability_status=supplier.availability_status,
            verification_level=supplier.verification_level,
            score=total_score,
            score_breakdown={
                "verification_component": str(verification_component),
                "reputation_component": str(reputation_component),
                "availability_component": str(availability_component),
                "capacity_component": str(capacity_component),
                "total_score": str(total_score),
            },
        )

    @staticmethod
    def _availability_bonus(supplier: ServiceSupplier) -> Decimal:
        return Decimal("1") if supplier.availability_status == AvailabilityStatus.AVAILABLE else Decimal("0")

    @staticmethod
    def _capacity_bonus(supplier: ServiceSupplier, capacity_exceeded_by_id: dict) -> Decimal:
        """1 unless the supplier has an active CapacityRule that's currently exceeded."""
        return Decimal("0") if capacity_exceeded_by_id.get(supplier.id, False) else Decimal("1")
