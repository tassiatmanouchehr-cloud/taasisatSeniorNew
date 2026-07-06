"""
Policy Service.

Provides the API for creating, versioning, activating, and resolving policies.
Ensures only one version is active at a time per policy, and that version
history is immutable.

Usage:
    from apps.kernel.services import PolicyService

    # Create a policy
    policy = PolicyService.create_policy(
        tenant_id=tenant.id,
        policy_type="commission",
        name="Platform Commission Q1 2026",
        owner_module="M05",
        rule_payload={"rate": 0.15, "min": 5000},
        effective_from=timezone.now(),
    )

    # Get active version for a policy type
    version = PolicyService.get_active_version(
        tenant_id=tenant.id,
        policy_type="commission",
    )

    # Get the rule payload
    rules = version.rule_payload  # {"rate": 0.15, "min": 5000}

References:
- ADR-001.16 (Policies are versioned)
- ADR-001.17 (No hard-coded business policy)
- Phase 0.5 Deliverable 12 (Policy lifecycle)
"""

import logging
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.kernel.models.policy import (
    PolicyDefinition,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
)

logger = logging.getLogger(__name__)


class PolicyService:
    """
    Central service for policy lifecycle management.

    Key invariants:
    - Only one version active at a time per policy
    - Active/superseded versions are immutable (rule_payload cannot change)
    - Version history is never deleted
    - Activating a new version supersedes the previous active version
    """

    @classmethod
    @transaction.atomic
    def create_policy(
        cls,
        *,
        tenant_id: uuid.UUID,
        policy_type: str,
        name: str,
        owner_module: str,
        rule_payload: dict[str, Any],
        effective_from: Any | None = None,
        description: str = "",
        scope_type: str = "",
        scope_id: uuid.UUID | None = None,
        validation_schema: dict | None = None,
        change_reason: str = "",
        created_by: uuid.UUID | None = None,
        auto_activate: bool = False,
    ) -> PolicyVersion:
        """
        Create a new policy with its first version.

        If auto_activate=True, the version is immediately activated.
        Otherwise, it's created in DRAFT status for review.

        Returns the created PolicyVersion.
        """
        if effective_from is None:
            effective_from = timezone.now()

        # Create or get the policy definition
        policy_def, created = PolicyDefinition.objects.get_or_create(
            tenant_id=tenant_id,
            policy_type=policy_type,
            name=name,
            defaults={
                "owner_module": owner_module,
                "description": description,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "status": PolicyStatus.ACTIVE if auto_activate else PolicyStatus.DRAFT,
                "current_version_number": 1,
            },
        )

        if not created:
            policy_def.current_version_number += 1
            policy_def.save(update_fields=["current_version_number", "updated_at"])

        version_number = policy_def.current_version_number

        # Create the version
        status = PolicyVersionStatus.ACTIVE if auto_activate else PolicyVersionStatus.DRAFT
        version = PolicyVersion.objects.create(
            tenant_id=tenant_id,
            policy=policy_def,
            version_number=version_number,
            rule_payload=rule_payload,
            validation_schema=validation_schema,
            effective_from=effective_from,
            status=status,
            change_reason=change_reason,
            created_by=created_by,
            approved_by=created_by if auto_activate else None,
            approved_at=timezone.now() if auto_activate else None,
        )

        # If auto-activating, supersede any previous active version
        if auto_activate:
            cls._supersede_previous(policy_def, version)
            if policy_def.status != PolicyStatus.ACTIVE:
                policy_def.status = PolicyStatus.ACTIVE
                policy_def.save(update_fields=["status", "updated_at"])

        logger.info(
            "Policy version created: %s v%d (type=%s, status=%s)",
            name, version_number, policy_type, status,
        )

        return version

    @classmethod
    @transaction.atomic
    def activate_version(
        cls,
        version_id: uuid.UUID,
        *,
        approved_by: uuid.UUID | None = None,
    ) -> PolicyVersion:
        """
        Activate a draft/pending policy version.

        Supersedes any currently active version of the same policy.
        """
        version = PolicyVersion.objects.select_for_update().get(id=version_id)

        if version.status not in (PolicyVersionStatus.DRAFT, PolicyVersionStatus.PENDING_APPROVAL):
            raise ValueError(
                f"Cannot activate a version in '{version.status}' status. "
                f"Only draft or pending_approval versions can be activated."
            )

        # Supersede previous active version
        cls._supersede_previous(version.policy, version)

        # Activate this version
        version.status = PolicyVersionStatus.ACTIVE
        version.approved_by = approved_by
        version.approved_at = timezone.now()
        version.save(update_fields=["status", "approved_by", "approved_at"])

        # Ensure policy definition is active
        policy_def = version.policy
        if policy_def.status != PolicyStatus.ACTIVE:
            policy_def.status = PolicyStatus.ACTIVE
            policy_def.save(update_fields=["status", "updated_at"])

        logger.info(
            "Policy version activated: %s v%d",
            policy_def.name, version.version_number,
        )

        return version

    @classmethod
    def get_active_version(
        cls,
        *,
        tenant_id: uuid.UUID,
        policy_type: str,
        policy_name: str | None = None,
        scope_type: str = "",
        scope_id: uuid.UUID | None = None,
        at_time: Any | None = None,
    ) -> PolicyVersion | None:
        """
        Get the currently active version for a policy type.

        If multiple policies of the same type exist (different names/scopes),
        filters by name and/or scope.

        Args:
            tenant_id: Tenant context.
            policy_type: Policy type key.
            policy_name: Specific policy name (if multiple per type).
            scope_type: Scope filter.
            scope_id: Scope entity ID filter.
            at_time: Point-in-time resolution (default: now).

        Returns:
            The active PolicyVersion, or None if no active version exists.
        """
        if at_time is None:
            at_time = timezone.now()

        # Find the policy definition
        qs = PolicyDefinition.objects.filter(
            tenant_id=tenant_id,
            policy_type=policy_type,
            status=PolicyStatus.ACTIVE,
        )
        if policy_name:
            qs = qs.filter(name=policy_name)
        if scope_type:
            qs = qs.filter(scope_type=scope_type)
        if scope_id:
            qs = qs.filter(scope_id=scope_id)

        policy_def = qs.first()
        if not policy_def:
            return None

        # Find active version within effective date range
        version = PolicyVersion.objects.filter(
            policy=policy_def,
            status=PolicyVersionStatus.ACTIVE,
            effective_from__lte=at_time,
        ).filter(
            models_q_effective_until(at_time),
        ).first()

        return version

    @classmethod
    def deprecate_policy(
        cls,
        policy_id: uuid.UUID,
    ) -> PolicyDefinition:
        """Mark a policy as deprecated (no longer accepting new versions)."""
        policy_def = PolicyDefinition.objects.get(id=policy_id)
        policy_def.status = PolicyStatus.DEPRECATED
        policy_def.save(update_fields=["status", "updated_at"])
        logger.info("Policy deprecated: %s", policy_def.name)
        return policy_def

    @classmethod
    def _supersede_previous(cls, policy_def: PolicyDefinition, new_version: PolicyVersion):
        """Supersede any currently active version of this policy."""
        active_versions = PolicyVersion.objects.filter(
            policy=policy_def,
            status=PolicyVersionStatus.ACTIVE,
        ).exclude(id=new_version.id)

        for old_version in active_versions:
            old_version.status = PolicyVersionStatus.SUPERSEDED
            old_version.superseded_by = new_version.id
            old_version.effective_until = timezone.now()
            old_version.save(update_fields=["status", "superseded_by", "effective_until"])


def models_q_effective_until(at_time):
    """Filter for versions whose effective_until has not passed."""
    from django.db.models import Q

    return Q(effective_until__isnull=True) | Q(effective_until__gt=at_time)
