"""
RBAC Configuration wrapper — Module 08 RBAC Enforcement foundation.

PermissionService must never call ConfigResolver directly — all Module 08
config keys and defaults are centralized here, mirroring
apps.booking.services.configuration.BookingConfiguration.

RBAC Enforcement-Toggle Emergency Control (approved architecture decision,
2026-07-20): `rbac.enforcement.enabled` is a platform emergency control,
not a self-service configuration setting. `set_enforcement_enabled()` is
the ONLY sanctioned write path for this key — there is deliberately no
Admin Portal, Django Admin, public UI, internal application UI, or API
mutation surface. The only caller is
`apps.kernel.management.commands.set_rbac_enforcement`, an operator-run
management command. `get_enforcement_status()` backs the read-only
Admin Portal visibility page (apps.admin_portal.views.rbac_enforcement_status).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import transaction

from apps.kernel.models.audit import AuditLog
from apps.kernel.models.configuration import (
    ConfigurationKey,
    ConfigurationValue,
    OverridePolicy,
    ScopeLevel,
    ValueType,
)
from apps.kernel.models.tenant import Tenant
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.config_resolver import ConfigResolver

ENFORCEMENT_ENABLED_KEY = "rbac.enforcement.enabled"

DEFAULT_ENFORCEMENT_ENABLED = True

SOURCE_MODULE = "M08"

ACTION_CHANGED = "rbac.enforcement.changed"
ACTION_NO_OP = "rbac.enforcement.no_op"


class RBACConfigurationError(Exception):
    """Raised on any invalid input to a RBACConfiguration write operation.

    Never raised silently swallowed by a caller — every write path
    (currently only the set_rbac_enforcement management command) must
    surface this as an operator-visible failure."""


@dataclass(frozen=True)
class EnforcementStatus:
    """Read-only snapshot for the Admin Portal status page and the
    management command's own confirmation output."""

    tenant_id: uuid.UUID
    enabled: bool
    source: str  # "default" (no override exists) or "override" (explicit ConfigurationValue)
    last_changed_at: datetime | None = None
    last_changed_by: str = ""
    last_change_reason: str = ""


class RBACConfiguration:
    """Central resolver for all Module 08 RBAC configuration values."""

    @classmethod
    def get_enforcement_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            ENFORCEMENT_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_ENFORCEMENT_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_ENFORCEMENT_ENABLED)

    @classmethod
    def get_enforcement_status(cls, *, tenant_id: uuid.UUID) -> EnforcementStatus:
        """Read-only: effective enforcement state for `tenant_id`, whether it
        comes from an explicit override or the implicit platform default,
        and the most recent actual change recorded in the audit log (if
        any). Never reads or writes the cache directly — bypasses
        ConfigResolver's cache so the status page always reflects the
        current database state, not a possibly-stale cached value."""
        override = cls._get_active_override(tenant_id=tenant_id)
        if override is None:
            enabled, source = DEFAULT_ENFORCEMENT_ENABLED, "default"
        else:
            enabled, source = cls._to_bool(override.value, DEFAULT_ENFORCEMENT_ENABLED), "override"

        last_change = (
            AuditLog.objects.filter(
                tenant_id=tenant_id,
                module_id=SOURCE_MODULE,
                resource_type="ConfigurationValue",
                action=ACTION_CHANGED,
            )
            .order_by("-occurred_at")
            .first()
        )

        return EnforcementStatus(
            tenant_id=tenant_id,
            enabled=enabled,
            source=source,
            last_changed_at=last_change.occurred_at if last_change else None,
            last_changed_by=last_change.actor_display if last_change else "",
            last_change_reason=last_change.reason if last_change else "",
        )

    @classmethod
    def set_enforcement_enabled(
        cls,
        *,
        tenant_id: uuid.UUID,
        enabled: bool,
        actor_display: str,
        reason: str,
        correlation_id: uuid.UUID | None = None,
        source: str = "management_command",
        operation: str = "set_rbac_enforcement",
    ) -> EnforcementStatus:
        """The ONLY sanctioned write path for `rbac.enforcement.enabled`.

        Enforces: tenant existence, mandatory actor identity, mandatory
        reason, concurrency-safe read-modify-write, an immutable audit
        record for every actual change, and post-commit cache
        invalidation. Same-value requests are idempotent no-ops: no new
        ConfigurationValue version is written, but a distinct
        "no_op" audit event is still recorded so a repeated command
        invocation is never silently invisible in the audit trail.

        Never touches any configuration key other than
        ENFORCEMENT_ENABLED_KEY.
        """
        tenant_id = cls._require_uuid(tenant_id, "tenant_id")
        actor_display = (actor_display or "").strip()
        if not actor_display:
            raise RBACConfigurationError("actor_display is required and cannot be empty.")
        reason = (reason or "").strip()
        if not reason:
            raise RBACConfigurationError("reason is required and cannot be empty.")
        if not Tenant.objects.filter(id=tenant_id).exists():
            raise RBACConfigurationError(f"No tenant found with id {tenant_id}.")

        with transaction.atomic():
            config_key, _ = ConfigurationKey.objects.get_or_create(
                key=ENFORCEMENT_ENABLED_KEY,
                defaults={
                    "owner_module": SOURCE_MODULE,
                    "scope_level": ScopeLevel.TENANT,
                    "value_type": ValueType.BOOLEAN,
                    "default_value": DEFAULT_ENFORCEMENT_ENABLED,
                    "override_policy": OverridePolicy.TENANT_OVERRIDE,
                    "audit_class": "security",
                    "description": (
                        "Emergency control: whether PermissionService.require() "
                        "enforces RBAC for this tenant. Mutable only through "
                        "the set_rbac_enforcement management command."
                    ),
                },
            )

            existing = (
                ConfigurationValue.objects.select_for_update()
                .filter(
                    tenant_id=tenant_id,
                    config_key=config_key,
                    scope_type=ScopeLevel.TENANT,
                    is_active=True,
                )
                .first()
            )
            previous_enabled = (
                cls._to_bool(existing.value, DEFAULT_ENFORCEMENT_ENABLED) if existing else DEFAULT_ENFORCEMENT_ENABLED
            )
            previous_source = "override" if existing else "default"

            if previous_enabled == enabled:
                AuditService.log_security(
                    tenant_id=tenant_id,
                    action=ACTION_NO_OP,
                    resource_type="ConfigurationValue",
                    module_id=SOURCE_MODULE,
                    resource_id=existing.id if existing else None,
                    actor_type="operator",
                    actor_display=actor_display,
                    before={"enabled": previous_enabled, "source": previous_source},
                    after={"enabled": enabled, "source": previous_source},
                    reason=reason,
                    correlation_id=correlation_id,
                    metadata={"source": source, "operation": operation, "no_op": True},
                )
                return EnforcementStatus(
                    tenant_id=tenant_id,
                    enabled=previous_enabled,
                    source=previous_source,
                    last_changed_at=existing.updated_at if existing else None,
                    last_changed_by=actor_display,
                    last_change_reason=reason,
                )

            if existing is not None:
                existing.value = enabled
                existing.change_reason = reason
                existing.save()
                config_value = existing
            else:
                config_value = ConfigurationValue.objects.create(
                    tenant_id=tenant_id,
                    config_key=config_key,
                    scope_type=ScopeLevel.TENANT,
                    value=enabled,
                    is_active=True,
                    change_reason=reason,
                )

            AuditService.log_security(
                tenant_id=tenant_id,
                action=ACTION_CHANGED,
                resource_type="ConfigurationValue",
                module_id=SOURCE_MODULE,
                resource_id=config_value.id,
                actor_type="operator",
                actor_display=actor_display,
                before={"enabled": previous_enabled, "source": previous_source},
                after={"enabled": enabled, "source": "override"},
                reason=reason,
                correlation_id=correlation_id,
                metadata={"source": source, "operation": operation, "no_op": False},
            )

            transaction.on_commit(lambda: ConfigResolver.invalidate(ENFORCEMENT_ENABLED_KEY, tenant_id=tenant_id))

        return EnforcementStatus(
            tenant_id=tenant_id,
            enabled=enabled,
            source="override",
            last_changed_at=config_value.updated_at,
            last_changed_by=actor_display,
            last_change_reason=reason,
        )

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _get_active_override(cls, *, tenant_id: uuid.UUID) -> ConfigurationValue | None:
        return (
            ConfigurationValue.objects.filter(
                tenant_id=tenant_id,
                config_key__key=ENFORCEMENT_ENABLED_KEY,
                scope_type=ScopeLevel.TENANT,
                is_active=True,
            )
            .order_by("-updated_at")
            .first()
        )

    @staticmethod
    def _require_uuid(value: Any, field_name: str) -> uuid.UUID:
        if not value:
            raise RBACConfigurationError(f"{field_name} is required.")
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except ValueError:
            raise RBACConfigurationError(f"{field_name} must be a valid UUID (got {value!r}).") from None

    @staticmethod
    def _to_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default
