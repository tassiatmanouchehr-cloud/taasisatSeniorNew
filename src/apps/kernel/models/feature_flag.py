"""
Feature Flag model.

Supports tenant-aware feature toggles with multiple evaluation strategies:
- Boolean: simple on/off per tenant
- Percentage: gradual rollout (0-100% of actors)
- Actor list: explicit allowlist/blocklist of actor IDs
- Rule-based: JSON rules evaluated at runtime (future)

Feature flags enable:
- Gradual rollout of new features
- Kill switches for emergency disabling
- A/B experiments (percentage-based)
- Tenant-specific feature gating
- Actor-targeted early access

References:
- ADR-001.17 (No hard-coded business policy)
- Phase 0.5 Deliverable 14 (FeatureFlag owned by M25, lifecycle by M19)
- Phase 1 Implementation Plan: Sprint 2 — Feature Flag Foundation
"""

import uuid

from django.db import models


class FlagType(models.TextChoices):
    """Feature flag evaluation strategies."""

    BOOLEAN = "boolean", "Boolean (on/off)"
    PERCENTAGE = "percentage", "Percentage Rollout"
    ACTOR_LIST = "actor_list", "Actor Allowlist"
    RULE_BASED = "rule_based", "Rule-Based (JSON rules)"


class FlagStatus(models.TextChoices):
    """Feature flag lifecycle states."""

    DRAFT = "draft", "Draft"
    ENABLED = "enabled", "Enabled"
    DISABLED = "disabled", "Disabled"
    ARCHIVED = "archived", "Archived"


class FeatureFlag(models.Model):
    """
    Tenant-aware feature flag with targeting rules.

    Evaluation logic is in the FeatureFlagService. This model stores
    the flag definition and targeting configuration.

    Kill switches (kill_switch=True) override all other evaluation
    and immediately disable the feature.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    # Identity
    key = models.CharField(
        max_length=200,
        help_text="Flag key, e.g., 'feature.new_matching_algorithm'.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for admin display.",
    )
    description = models.TextField(blank=True)

    # Type and status
    flag_type = models.CharField(
        max_length=20,
        choices=FlagType.choices,
        default=FlagType.BOOLEAN,
    )
    status = models.CharField(
        max_length=20,
        choices=FlagStatus.choices,
        default=FlagStatus.DRAFT,
        db_index=True,
    )

    # Evaluation parameters
    is_enabled = models.BooleanField(
        default=False,
        help_text="For boolean flags: the on/off state.",
    )
    percentage = models.IntegerField(
        default=0,
        help_text="For percentage flags: rollout percentage (0-100).",
    )
    actor_allowlist = models.JSONField(
        default=list,
        blank=True,
        help_text="For actor_list flags: list of actor UUIDs that get the feature.",
    )
    actor_blocklist = models.JSONField(
        default=list,
        blank=True,
        help_text="Actors explicitly excluded from the feature.",
    )
    targeting_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="For rule_based flags: JSON evaluation rules.",
    )

    # Kill switch
    kill_switch = models.BooleanField(
        default=False,
        help_text="Emergency disable. Overrides all other evaluation — feature is OFF.",
    )

    # Ownership
    owner_module = models.CharField(
        max_length=10,
        blank=True,
        help_text="Module that owns this flag, e.g., 'M02'.",
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = 'kernel"."feature_flag'
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"
        unique_together = [("tenant_id", "key")]
        ordering = ["key"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_flag_tenant_status",
            ),
        ]

    def __str__(self):
        return f"{self.key} [{self.status}] ({self.get_flag_type_display()})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)
