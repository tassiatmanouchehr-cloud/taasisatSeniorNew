"""
Feature Flag evaluation service.

Evaluates feature flags based on their type, status, and targeting rules.
Results are cached for performance.

Usage:
    from apps.kernel.services import FeatureFlagService

    # Simple boolean check
    if FeatureFlagService.is_enabled("feature.new_ui", tenant_id=tenant.id):
        ...

    # Percentage-based with actor context
    if FeatureFlagService.is_enabled(
        "feature.new_matching",
        tenant_id=tenant.id,
        actor_id=person.id,
    ):
        ...

References:
- ADR-001.17 (No hard-coded business policy)
- Phase 0.5 Deliverable 18 (Validation #28: flags per-tenant, per-actor, percentage)
- Phase 1 Implementation Plan: Sprint 2 — Feature Flag Foundation
"""

import hashlib
import logging
import uuid

from django.core.cache import cache

from apps.kernel.models.feature_flag import FeatureFlag, FlagStatus, FlagType

logger = logging.getLogger(__name__)

# Cache TTL for flag evaluations (seconds)
FLAG_CACHE_TTL = 60  # 1 minute (shorter than config — flags change more often)


class FeatureFlagService:
    """
    Central service for evaluating feature flags.

    Evaluation logic:
    1. Kill switch → always False
    2. Status != enabled → always False
    3. Actor in blocklist → False
    4. Actor in allowlist → True
    5. By flag type:
       - boolean: return is_enabled
       - percentage: hash(actor_id) % 100 < percentage
       - actor_list: actor_id in allowlist
       - rule_based: evaluate targeting_rules (future)
    """

    @classmethod
    def is_enabled(
        cls,
        key: str,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        use_cache: bool = True,
    ) -> bool:
        """
        Evaluate whether a feature flag is enabled for the given context.

        Args:
            key: Flag key, e.g., 'feature.new_matching_algorithm'.
            tenant_id: Tenant to evaluate for.
            actor_id: Optional actor ID for percentage/actor-based evaluation.
            use_cache: Whether to use cached results (default True).

        Returns:
            True if the feature is enabled for this context, False otherwise.
            Returns False if the flag doesn't exist (safe default).
        """
        # Build cache key
        cache_key = cls._build_cache_key(key, tenant_id, actor_id)

        # Check cache
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        # Evaluate
        result = cls._evaluate(key, tenant_id, actor_id)

        # Cache result
        if use_cache:
            cache.set(cache_key, result, timeout=FLAG_CACHE_TTL)

        return result

    @classmethod
    def _evaluate(
        cls,
        key: str,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None,
    ) -> bool:
        """Core evaluation logic."""
        try:
            flag = FeatureFlag.objects.get(tenant_id=tenant_id, key=key)
        except FeatureFlag.DoesNotExist:
            logger.debug("Flag not found: %s (tenant=%s) → False", key, tenant_id)
            return False

        # Kill switch overrides everything
        if flag.kill_switch:
            logger.debug("Flag kill-switched: %s → False", key)
            return False

        # Must be enabled status
        if flag.status != FlagStatus.ENABLED:
            logger.debug("Flag not enabled: %s (status=%s) → False", key, flag.status)
            return False

        # Check blocklist (explicit exclusion)
        if actor_id and str(actor_id) in [str(a) for a in flag.actor_blocklist]:
            logger.debug("Flag blocked for actor: %s → False", key)
            return False

        # Check allowlist (explicit inclusion — overrides percentage)
        if actor_id and str(actor_id) in [str(a) for a in flag.actor_allowlist]:
            logger.debug("Flag allowed for actor: %s → True", key)
            return True

        # Evaluate by type
        if flag.flag_type == FlagType.BOOLEAN:
            return flag.is_enabled

        elif flag.flag_type == FlagType.PERCENTAGE:
            if not actor_id:
                # Without actor context, use flag's is_enabled as fallback
                return flag.is_enabled
            # Deterministic percentage check using hash
            return cls._in_percentage(key, actor_id, flag.percentage)

        elif flag.flag_type == FlagType.ACTOR_LIST:
            if not actor_id:
                return False
            return str(actor_id) in [str(a) for a in flag.actor_allowlist]

        elif flag.flag_type == FlagType.RULE_BASED:
            # Future: evaluate targeting_rules JSON
            # For now, fall back to is_enabled
            return flag.is_enabled

        return False

    @classmethod
    def _in_percentage(cls, key: str, actor_id: uuid.UUID, percentage: int) -> bool:
        """
        Deterministic percentage check.

        Uses hash(key + actor_id) to produce a stable 0-99 bucket.
        Same actor always gets the same result for the same flag.
        """
        hash_input = f"{key}:{actor_id}".encode()
        hash_value = int(hashlib.sha256(hash_input).hexdigest(), 16)
        bucket = hash_value % 100
        return bucket < percentage

    @classmethod
    def invalidate(cls, key: str, tenant_id: uuid.UUID) -> None:
        """Invalidate cached evaluation for a flag."""
        # Invalidate base key (without actor — actor-specific will expire naturally)
        cache_key = cls._build_cache_key(key, tenant_id, None)
        cache.delete(cache_key)
        logger.debug("Flag cache invalidated: %s for tenant %s", key, tenant_id)

    @classmethod
    def _build_cache_key(
        cls,
        key: str,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None,
    ) -> str:
        """Build deterministic cache key."""
        parts = [f"flag:{tenant_id}:{key}"]
        if actor_id:
            parts.append(f"actor={actor_id}")
        return ":".join(parts)
