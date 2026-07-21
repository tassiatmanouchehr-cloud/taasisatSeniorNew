"""
Matching Configuration wrapper — Module 02 Matching Engine.

Eligibility and ranking code must never call ConfigResolver directly. All
matching-specific config keys, defaults, and CCS lookup details are
centralized here so the rest of the matching engine only ever depends on
this wrapper's API, not on the kernel config plumbing.

Per ADR-001.17 (No hard-coded business policy) / ADR-02-22 (MVP uses
configurable rule-based ranking).
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

MAX_CANDIDATES_KEY = "matching.ranking.max_candidates"
MIN_VERIFICATION_LEVEL_KEY = "matching.eligibility.min_verification_level"
VERIFICATION_WEIGHT_KEY = "matching.ranking.weight.verification"
REPUTATION_WEIGHT_KEY = "matching.ranking.weight.reputation"
AVAILABILITY_WEIGHT_KEY = "matching.ranking.weight.availability"

DEFAULT_MAX_CANDIDATES = 20
DEFAULT_MIN_VERIFICATION_LEVEL = ""  # empty string = no threshold enforced
DEFAULT_RANKING_WEIGHTS = {
    "verification": 1.0,
    "reputation": 1.0,
    "availability": 0.5,
}


class MatchingConfiguration:
    """Central resolver for all Matching Engine configuration values.

    None of these config keys are pre-registered as ConfigurationKey rows
    in this sprint — every lookup goes through get_or_default() so the
    engine works with sane defaults even before an operator registers
    tenant-specific overrides.
    """

    @classmethod
    def get_max_candidates(cls, *, tenant_id: uuid.UUID) -> int:
        value = ConfigResolver.get_or_default(
            MAX_CANDIDATES_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_MAX_CANDIDATES,
        )
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULT_MAX_CANDIDATES

    @classmethod
    def get_minimum_verification_level(cls, *, tenant_id: uuid.UUID) -> str:
        value = ConfigResolver.get_or_default(
            MIN_VERIFICATION_LEVEL_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_MIN_VERIFICATION_LEVEL,
        )
        return value or ""

    @classmethod
    def get_ranking_weights(cls, *, tenant_id: uuid.UUID) -> dict:
        return {
            "verification": cls._get_float(VERIFICATION_WEIGHT_KEY, tenant_id, DEFAULT_RANKING_WEIGHTS["verification"]),
            "reputation": cls._get_float(REPUTATION_WEIGHT_KEY, tenant_id, DEFAULT_RANKING_WEIGHTS["reputation"]),
            "availability": cls._get_float(AVAILABILITY_WEIGHT_KEY, tenant_id, DEFAULT_RANKING_WEIGHTS["availability"]),
        }

    @classmethod
    def _get_float(cls, key: str, tenant_id: uuid.UUID, default: float) -> float:
        value = ConfigResolver.get_or_default(key, tenant_id=tenant_id, default=default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
