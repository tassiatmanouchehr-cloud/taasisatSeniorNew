"""
CCS Configuration models.

Implements the Cross-Module Configuration System (CCS) per Module 25.
Every configurable behavior in the platform is registered as a ConfigurationKey
with a default value. Tenants/organizations/actors can override values through
ConfigurationValue records, resolved in a strict scope hierarchy.

CCS Envelope per Module 25:
- config_key, owner_module, schema_version, scope_level
- value_type, default_value, override_policy
- change_requires_approval, activation_mode, rollback_supported
- audit_class

References:
- ADR-001.15 (Configuration uses CCS)
- ADR-001.17 (No hard-coded business policy)
- Module 25: 05_Config_Kernel/CCS_Kernel_Envelope.md
- Phase 0.5 Deliverable 14 (ConfigurationKey/Value owned by M25)
"""

import uuid

from django.db import models


class ScopeLevel(models.TextChoices):
    """Configuration scope levels — resolution hierarchy (lowest to highest)."""

    PLATFORM = "platform", "Platform"
    TENANT = "tenant", "Tenant"
    ORGANIZATION = "organization", "Organization"
    BRANCH = "branch", "Branch"
    ROLE = "role", "Role"
    ACTOR = "actor", "Actor"


class ValueType(models.TextChoices):
    """Supported configuration value types."""

    BOOLEAN = "boolean", "Boolean"
    STRING = "string", "String"
    NUMBER = "number", "Number"
    INTEGER = "integer", "Integer"
    ENUM = "enum", "Enum"
    OBJECT = "object", "Object (JSON)"
    ARRAY = "array", "Array (JSON)"


class OverridePolicy(models.TextChoices):
    """Controls how/if a configuration key can be overridden."""

    LOCKED = "locked", "Locked (no override allowed)"
    INHERITABLE = "inheritable", "Inheritable (child scopes inherit)"
    TENANT_OVERRIDE = "tenant_override", "Tenant Override Allowed"
    ROLE_OVERRIDE = "role_override", "Role Override Allowed"
    FULL_OVERRIDE = "full_override", "Full Override (any scope)"


class ActivationMode(models.TextChoices):
    """When a configuration change takes effect."""

    IMMEDIATE = "immediate", "Immediate"
    SCHEDULED = "scheduled", "Scheduled"
    NEXT_CYCLE = "next_cycle", "Next Cycle"


class ConfigurationKey(models.Model):
    """
    Registry of all CCS configuration keys.

    Each key has exactly one owning module and a defined scope, value type,
    and override policy. Keys are namespaced (e.g., 'marketplace.supplier_model').

    This is a platform-global entity — NOT tenant-scoped.
    Modules register their keys at startup or via migration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identity
    key = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
        help_text="Namespaced config key, e.g., 'marketplace.supplier_model'.",
    )
    owner_module = models.CharField(
        max_length=10,
        help_text="Module that owns this key, e.g., 'M19'.",
    )

    # Schema
    schema_version = models.CharField(max_length=10, default="1.0")
    scope_level = models.CharField(
        max_length=20,
        choices=ScopeLevel.choices,
        default=ScopeLevel.TENANT,
        help_text="Maximum scope at which this key can be set.",
    )
    value_type = models.CharField(
        max_length=20,
        choices=ValueType.choices,
        default=ValueType.STRING,
    )
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Default value when no override exists. Stored as JSON.",
    )
    allowed_values = models.JSONField(
        null=True,
        blank=True,
        help_text="For enum type: list of allowed values.",
    )
    validation_schema = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON Schema for validating values (object/array types).",
    )

    # Governance
    override_policy = models.CharField(
        max_length=20,
        choices=OverridePolicy.choices,
        default=OverridePolicy.TENANT_OVERRIDE,
    )
    change_requires_approval = models.BooleanField(
        default=False,
        help_text="Whether changes require platform-owner approval.",
    )
    activation_mode = models.CharField(
        max_length=20,
        choices=ActivationMode.choices,
        default=ActivationMode.IMMEDIATE,
    )
    rollback_supported = models.BooleanField(default=True)
    is_sensitive = models.BooleanField(
        default=False,
        help_text="Sensitive values are encrypted/masked in logs.",
    )

    # Audit
    audit_class = models.CharField(
        max_length=20,
        default="standard",
    )

    # Metadata
    description = models.TextField(blank=True)
    deprecated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, this key is deprecated and should not be used.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kernel"."configuration_key'
        verbose_name = "Configuration Key"
        verbose_name_plural = "Configuration Keys"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} ({self.value_type}, scope={self.scope_level})"


class ConfigurationValue(models.Model):
    """
    Scoped override for a configuration key.

    If no override exists at a given scope, the system falls through to
    broader scopes and ultimately to the key's default_value.

    Resolution order (most specific wins):
    1. Actor-specific override
    2. Role-specific override
    3. Branch-specific override
    4. Organization-specific override
    5. Tenant-specific override
    6. Platform default (ConfigurationKey.default_value)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant this override belongs to.",
    )
    config_key = models.ForeignKey(
        ConfigurationKey,
        on_delete=models.CASCADE,
        related_name="overrides",
    )

    # Scope
    scope_type = models.CharField(
        max_length=20,
        choices=ScopeLevel.choices,
        default=ScopeLevel.TENANT,
        help_text="At which level this override applies.",
    )
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the scoped entity (org, branch, actor). Null for tenant scope.",
    )

    # Value
    value = models.JSONField(
        help_text="The override value. Must conform to the key's value_type.",
    )

    # Lifecycle
    is_active = models.BooleanField(default=True, db_index=True)
    effective_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this override becomes active. Null = immediately.",
    )
    effective_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this override expires. Null = no expiry.",
    )

    # Governance
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    change_reason = models.TextField(
        blank=True,
        help_text="Why this override was created/changed.",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = 'kernel"."configuration_value'
        verbose_name = "Configuration Value"
        verbose_name_plural = "Configuration Values"
        indexes = [
            models.Index(
                fields=["tenant_id", "config_key", "is_active"],
                name="idx_config_val_tenant_key",
            ),
            models.Index(
                fields=["config_key", "scope_type", "scope_id"],
                name="idx_config_val_scope",
            ),
        ]

    def __str__(self):
        return f"{self.config_key.key} = {self.value} (scope={self.scope_type})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)
