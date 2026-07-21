"""
Ranking Service — Module 02 Matching Engine.

Strategy-pattern ranking of already-eligible candidates. Per ADR-02-22
(MVP uses configurable rule-based ranking), scoring weights come from
MatchingConfiguration — never a hardcoded ConfigResolver call inside a
strategy.

Ranking is deterministic: identical inputs always produce an identical
ordering. Ties are broken by supplier id (stable, reproducible).
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from .configuration import MatchingConfiguration

VERIFICATION_LEVEL_WEIGHTS = {
    "unverified": Decimal("0"),
    "basic": Decimal("1"),
    "advanced": Decimal("2"),
    "premium": Decimal("3"),
}


class RankingStrategy(ABC):
    """Base interface for pluggable ranking strategies."""

    @abstractmethod
    def score(self, *, order, supplier) -> tuple[Decimal, dict[str, Any]]:
        """Return (rank_score, score_breakdown) for a single supplier."""


class SimpleRankingStrategy(RankingStrategy):
    """
    First-pass deterministic ranking strategy.

    score = (verification_level weight * verification weight)
          + (reputation_score * reputation weight)
          + (availability bonus * availability weight)

    reputation_score is frequently null today (Module 06/14 doesn't
    populate it yet) and is treated as 0 in that case.
    """

    def score(self, *, order, supplier) -> tuple[Decimal, dict[str, Any]]:
        weights = MatchingConfiguration.get_ranking_weights(tenant_id=order.tenant_id)

        verification_level_weight = VERIFICATION_LEVEL_WEIGHTS.get(supplier.verification_level, Decimal("0"))
        verification_component = verification_level_weight * Decimal(str(weights["verification"]))

        reputation_score = supplier.reputation_score or Decimal("0")
        reputation_component = Decimal(reputation_score) * Decimal(str(weights["reputation"]))

        availability_bonus = Decimal("1") if supplier.availability_status == "available" else Decimal("0")
        availability_component = availability_bonus * Decimal(str(weights["availability"]))

        total = verification_component + reputation_component + availability_component

        breakdown = {
            "verification_level": supplier.verification_level,
            "verification_component": str(verification_component),
            "reputation_component": str(reputation_component),
            "availability_component": str(availability_component),
        }
        return total, breakdown


class RankingService:
    """Ranks a set of eligible ServiceSupplier candidates for an Order."""

    @classmethod
    def rank(cls, *, order, candidates: list, strategy: RankingStrategy | None = None):
        """
        Rank `candidates` (a list of ServiceSupplier instances, assumed
        already eligibility-filtered) best-first.

        Returns a list of (supplier, rank_score, score_breakdown) tuples,
        deterministically ordered: highest score first, ties broken by
        supplier id ascending.
        """
        strategy = strategy or SimpleRankingStrategy()

        scored = [(supplier, *strategy.score(order=order, supplier=supplier)) for supplier in candidates]
        scored.sort(key=lambda item: (-item[1], str(item[0].id)))
        return scored
