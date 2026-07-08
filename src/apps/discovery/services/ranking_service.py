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
        scored = [cls._score(supplier, weights) for supplier in suppliers]
        scored.sort(key=lambda item: (-item.score, str(item.supplier_id)))
        return scored

    @classmethod
    def _score(cls, supplier: ServiceSupplier, weights: dict[str, Decimal]) -> SearchResultItem:
        verification_component = _VERIFICATION_TIER.get(supplier.verification_level, Decimal("0")) * weights["verification"]
        reputation_component = (supplier.reputation_score or Decimal("0")) * weights["reputation"]
        availability_component = cls._availability_bonus(supplier) * weights["availability"]
        capacity_component = cls._capacity_bonus(supplier) * weights["capacity"]

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
    def _capacity_bonus(supplier: ServiceSupplier) -> Decimal:
        """1 unless the supplier has an active CapacityRule that's currently exceeded."""
        from apps.availability.services import CapacityService

        return Decimal("0") if CapacityService.is_capacity_exceeded(supplier=supplier) else Decimal("1")
