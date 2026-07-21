"""
Policy Versioning models.

Major business rules (matching, commission, pricing, cancellation, etc.)
are implemented as versioned policies. Each policy has immutable version
snapshots — policy history is never overwritten.

PolicyDefinition: The policy container (tenant-scoped, named, typed).
PolicyVersion: An immutable snapshot of the policy rules at a point in time.
Only one version is active at a time per policy.

References:
- ADR-001.16 (Policies are versioned)
- ADR-001.17 (No hard-coded business policy)
- Phase 0.5 Deliverable 8 (Extracted Policies — 44+ domains)
- Phase 0.5 Deliverable 11 (Configuration Aggregate — PolicyDefinition root)
- Phase 0.5 Deliverable 12 (Policy lifecycle: draft → active → deprecated → archived)
"""

import uuid

from django.db import models


class PolicyStatus(models.TextChoices):
    """PolicyDefinition lifecycle states."""

    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    DEPRECATED = "deprecated", "Deprecated"
    ARCHIVED = "archived", "Archived"


class PolicyVersionStatus(models.TextChoices):
    """PolicyVersion lifecycle states."""

    DRAFT = "draft", "Draft"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    ACTIVE = "active", "Active"
    SUPERSEDED = "superseded", "Superseded"


class PolicyDefinition(models.Model):
    """
    Versioned business policy container.

    Each PolicyDefinition represents one policy concept (e.g., 'commission_policy',
    'matching_ranking_policy', 'cancellation_policy'). It holds governance metadata
    while the actual rule payload lives in PolicyVersion records.

    Modules register their policies by creating PolicyDefinition records.
    The active version is resolved by the PolicyService at runtime.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    # Identity
    policy_type = models.CharField(
        max_length=100,
        help_text="Policy type key, e.g., 'commission', 'matching_ranking', 'cancellation'.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable policy name.",
    )
    description = models.TextField(blank=True)

    # Ownership
    owner_module = models.CharField(
        max_length=10,
        help_text="Module that owns this policy, e.g., 'M05'.",
    )

    # Scope (what does this policy apply to?)
    scope_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Scope: 'tenant', 'organization', 'service_category', 'supplier_type', etc.",
    )
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the scoped entity. Null for tenant-wide policies.",
    )

    # State
    status = models.CharField(
        max_length=20,
        choices=PolicyStatus.choices,
        default=PolicyStatus.DRAFT,
        db_index=True,
    )
    current_version_number = models.IntegerField(
        default=0,
        help_text="Latest version number. Incremented on each new version.",
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = 'kernel"."policy_definition'
        verbose_name = "Policy Definition"
        verbose_name_plural = "Policy Definitions"
        unique_together = [("tenant_id", "policy_type", "name")]
        ordering = ["policy_type", "name"]
        indexes = [
            models.Index(
                fields=["tenant_id", "policy_type", "status"],
                name="idx_policy_def_tenant_type",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.policy_type}) [{self.status}]"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)


class PolicyVersion(models.Model):
    """
    Immutable snapshot of a policy at a point in time.

    Once a PolicyVersion is activated, it becomes IMMUTABLE — never updated.
    Corrections require creating a new version that supersedes the old one.

    The rule_payload field holds the module-specific rule structure as JSONB.
    Each module defines its own payload schema (validated externally).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    # Relationship
    policy = models.ForeignKey(
        PolicyDefinition,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.IntegerField(
        help_text="Sequential version number within this policy.",
    )

    # Rule payload (module-specific)
    rule_payload = models.JSONField(
        help_text="Module-specific rule structure. Validated by the owning module.",
    )
    validation_schema = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON Schema for validating rule_payload (optional).",
    )

    # Effective dates
    effective_from = models.DateTimeField(
        help_text="When this version becomes active.",
    )
    effective_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this version expires. Null = no expiry (until superseded).",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=PolicyVersionStatus.choices,
        default=PolicyVersionStatus.DRAFT,
        db_index=True,
    )

    # Governance
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    change_reason = models.TextField(
        blank=True,
        help_text="Why this version was created (required for audit).",
    )
    superseded_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the version that superseded this one.",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'kernel"."policy_version'
        verbose_name = "Policy Version"
        verbose_name_plural = "Policy Versions"
        unique_together = [("policy", "version_number")]
        ordering = ["-version_number"]
        indexes = [
            models.Index(
                fields=["policy", "status", "effective_from"],
                name="idx_policy_ver_active",
            ),
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_policy_ver_tenant",
            ),
        ]

    def __str__(self):
        return f"{self.policy.name} v{self.version_number} [{self.status}]"

    def save(self, *args, **kwargs):
        """
        Enforce immutability for active/superseded versions.

        Allowed modifications on active/superseded versions (governance fields):
        - status (for lifecycle transitions: active → superseded)
        - superseded_by (records which version replaced this one)
        - effective_until (set when superseded)
        - approved_by (set during activation transition: draft → active)
        - approved_at (set during activation transition: draft → active)

        Forbidden modifications on active/superseded versions:
        - rule_payload (the actual policy rules — immutable after activation)
        - version_number, policy, validation_schema, effective_from, etc.
        """
        if not self._state.adding:
            if self.status in (PolicyVersionStatus.ACTIVE, PolicyVersionStatus.SUPERSEDED):
                allowed_update_fields = kwargs.get("update_fields")
                if allowed_update_fields:
                    # These fields may be modified during lifecycle transitions
                    allowed_on_active = {
                        "status",
                        "superseded_by",
                        "effective_until",
                        "approved_by",
                        "approved_at",
                    }
                    forbidden = set(allowed_update_fields) - allowed_on_active
                    if forbidden:
                        raise ValueError(
                            f"Cannot modify fields {forbidden} on an "
                            f"{self.status} policy version. Create a new version instead."
                        )
        super().save(*args, **kwargs)
