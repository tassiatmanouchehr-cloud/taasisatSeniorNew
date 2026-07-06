"""
CCS Configuration Resolver service.

Resolves configuration values using the CCS scope hierarchy:
1. Actor-specific override (most specific)
2. Role-specific override
3. Branch-specific override
4. Organization-specific override
5. Tenant-specific override
6. Platform default (ConfigurationKey.default_value)

Values are cached in Django's cache backend (Redis in production,
LocMemCache in dev/test) with configurable TTL.

Usage:
    from apps.kernel.services import ConfigResolver

    # Simple tenant-scoped resolution
    value = ConfigResolver.get("marketplace.supplier_model", tenant_id=tenant.id)

    # Full scope context
    value = ConfigResolver.get(
        "execution.presence.gps_required",
        tenant_id=tenant.id,
        scope_context={
            "organization_id": org.id,
            "branch_id": branch.id,
            "actor_id": person.id,
        },
    )

References:
- ADR-001.15 (Configuration uses CCS)
- Module 25: 05_Config_Kernel/CCS_Kernel_Envelope.md
- Phase 1 Implementation Plan: ConfigResolver with Redis caching
"""

import logging
import uuid
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel

logger = logging.getLogger(__name__)

# Cache TTL for resolved config values (seconds)
CONFIG_CACHE_TTL = 300  # 5 minutes


class ConfigResolver:
    """
    Central service for resolving CCS configuration values.

    Resolves values by traversing the scope hierarchy from most specific
    to least specific, returning the first matching override or the
    platform default.
    """

    # Scope resolution order (most specific first)
    SCOPE_PRIORITY = [
        ScopeLevel.ACTOR,
        ScopeLevel.ROLE,
        ScopeLevel.BRANCH,
        ScopeLevel.ORGANIZATION,
        ScopeLevel.TENANT,
        ScopeLevel.PLATFORM,
    ]

    @classmethod
    def get(
        cls,
        key: str,
        *,
        tenant_id: uuid.UUID,
        scope_context: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> Any:
        """
        Resolve a configuration value for the given context.

        Traverses scope hierarchy from most specific to platform default.
        Results are cached for performance.

        Args:
            key: Configuration key name, e.g., 'marketplace.supplier_model'.
            tenant_id: Tenant to resolve for.
            scope_context: Optional dict with scope IDs:
                - actor_id: UUID of the actor
                - role_id: UUID of the role
                - branch_id: UUID of the branch
                - organization_id: UUID of the organization
            use_cache: Whether to use cached values (default True).

        Returns:
            The resolved configuration value (Python native type from JSON).

        Raises:
            ConfigurationKey.DoesNotExist: If the key is not registered.
        """
        scope_context = scope_context or {}

        # Build cache key
        cache_key = cls._build_cache_key(key, tenant_id, scope_context)

        # Check cache first
        if use_cache:
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

        # Resolve from database
        value = cls._resolve_from_db(key, tenant_id, scope_context)

        # Cache the result
        if use_cache:
            cache.set(cache_key, value, timeout=CONFIG_CACHE_TTL)

        return value

    @classmethod
    def get_or_default(
        cls,
        key: str,
        *,
        tenant_id: uuid.UUID,
        default: Any = None,
        scope_context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Resolve a config value, returning `default` if key doesn't exist.

        Unlike get(), this does not raise if the key is unregistered.
        """
        try:
            return cls.get(key, tenant_id=tenant_id, scope_context=scope_context)
        except ConfigurationKey.DoesNotExist:
            return default

    @classmethod
    def invalidate(cls, key: str, tenant_id: uuid.UUID) -> None:
        """Invalidate cached value for a specific key+tenant."""
        # Invalidate all possible scope combinations by using a pattern
        # For simplicity, invalidate the base key (tenant-level)
        cache_key = cls._build_cache_key(key, tenant_id, {})
        cache.delete(cache_key)
        logger.debug("Config cache invalidated: %s for tenant %s", key, tenant_id)

    @classmethod
    def _resolve_from_db(
        cls,
        key: str,
        tenant_id: uuid.UUID,
        scope_context: dict[str, Any],
    ) -> Any:
        """Resolve value from database using scope hierarchy."""
        # Get the key definition
        config_key = ConfigurationKey.objects.get(key=key)

        now = timezone.now()

        # Query all active overrides for this key+tenant
        overrides = ConfigurationValue.objects.filter(
            config_key=config_key,
            tenant_id=tenant_id,
            is_active=True,
        ).filter(
            # Must be within effective date range
            models_q_effective_from(now),
        ).select_related("config_key")

        # Try each scope level from most specific to least specific
        for scope_level in cls.SCOPE_PRIORITY:
            scope_id = cls._get_scope_id(scope_level, scope_context, tenant_id)
            if scope_id is None and scope_level not in (ScopeLevel.TENANT, ScopeLevel.PLATFORM):
                continue

            matching = overrides.filter(scope_type=scope_level)
            if scope_level not in (ScopeLevel.TENANT, ScopeLevel.PLATFORM):
                matching = matching.filter(scope_id=scope_id)

            override = matching.first()
            if override:
                logger.debug(
                    "Config resolved: %s = %s (scope=%s)",
                    key, override.value, scope_level,
                )
                return override.value

        # Fall through to platform default
        logger.debug("Config resolved: %s = %s (default)", key, config_key.default_value)
        return config_key.default_value

    @classmethod
    def _get_scope_id(
        cls,
        scope_level: str,
        scope_context: dict[str, Any],
        tenant_id: uuid.UUID,
    ) -> uuid.UUID | None:
        """Map a scope level to the appropriate ID from context."""
        mapping = {
            ScopeLevel.ACTOR: "actor_id",
            ScopeLevel.ROLE: "role_id",
            ScopeLevel.BRANCH: "branch_id",
            ScopeLevel.ORGANIZATION: "organization_id",
            ScopeLevel.TENANT: None,  # tenant_id used directly
            ScopeLevel.PLATFORM: None,  # no scope_id needed
        }
        context_key = mapping.get(scope_level)
        if context_key:
            return scope_context.get(context_key)
        return None

    @classmethod
    def _build_cache_key(
        cls,
        key: str,
        tenant_id: uuid.UUID,
        scope_context: dict[str, Any],
    ) -> str:
        """Build a deterministic cache key for this resolution context."""
        parts = [f"config:{tenant_id}:{key}"]
        # Add scope context to cache key for specificity
        for scope_key in ("actor_id", "role_id", "branch_id", "organization_id"):
            if scope_key in scope_context and scope_context[scope_key]:
                parts.append(f"{scope_key}={scope_context[scope_key]}")
        return ":".join(parts)


def models_q_effective_from(now):
    """
    Build a Q filter for effective date range.

    Returns records where:
    - effective_from is NULL (immediately active) OR effective_from <= now
    - effective_until is NULL (no expiry) OR effective_until > now
    """
    from django.db.models import Q

    return (
        Q(effective_from__isnull=True) | Q(effective_from__lte=now)
    ) & (
        Q(effective_until__isnull=True) | Q(effective_until__gt=now)
    )
