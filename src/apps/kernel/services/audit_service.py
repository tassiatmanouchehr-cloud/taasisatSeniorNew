"""
Audit Service.

Provides the API for recording audit entries across all modules.
Every security-sensitive, financial, compliance, or material state change
must be recorded through this service.

Usage:
    from apps.kernel.services import AuditService

    AuditService.log(
        tenant_id=tenant.id,
        action="role.assign",
        resource_type="RoleAssignment",
        resource_id=assignment.id,
        module_id="M08",
        actor_id=request.user.person.id,
        after={"role": "platform-owner", "user": str(user.id)},
        audit_class="security",
        request=request,
    )

References:
- Module 25: Audit_Envelope_Standard.md
- Phase 0.5 Deliverable 12 (Entity Lifecycle — audit records are immutable)
- Phase 0.5 Deliverable 14 (AuditLog owned by M25, append-only)
"""

import logging
import uuid
from typing import Any

from apps.kernel.models.audit import AuditClassification, AuditLog

logger = logging.getLogger(__name__)


def _get_client_ip(request) -> str | None:
    """Extract client IP from Django request, handling proxies."""
    if request is None:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditService:
    """
    Central service for recording audit entries.

    All audit entries are append-only. Once created, they cannot be
    modified or deleted (enforced at the model level).
    """

    @staticmethod
    def log(
        *,
        tenant_id: uuid.UUID,
        action: str,
        resource_type: str,
        module_id: str,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "",
        actor_display: str = "",
        impersonator_id: uuid.UUID | None = None,
        resource_id: uuid.UUID | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        reason: str = "",
        correlation_id: uuid.UUID | None = None,
        audit_class: str = AuditClassification.STANDARD,
        retention_policy: str = "standard",
        metadata: dict[str, Any] | None = None,
        request=None,
    ) -> AuditLog:
        """
        Create an immutable audit record.

        Args:
            tenant_id: Tenant that owns this audit entry.
            action: Action performed, e.g., 'policy.publish', 'role.assign'.
            resource_type: Type of affected resource, e.g., 'Role', 'Tenant'.
            module_id: Module that owns this action, e.g., 'M08'.
            actor_id: Person who performed the action.
            actor_type: Type of actor ('person', 'system', 'integration').
            actor_display: Human-readable actor name.
            impersonator_id: Real actor if impersonating.
            resource_id: ID of the affected resource.
            before: State before change (redacted for sensitive data).
            after: State after change (redacted for sensitive data).
            reason: Human-provided reason for the action.
            correlation_id: Request chain correlation ID.
            audit_class: Classification (standard/financial/security/compliance).
            retention_policy: Retention policy identifier.
            metadata: Additional structured context.
            request: Django HTTP request (for IP/user-agent extraction).

        Returns:
            The created AuditLog instance (immutable after creation).
        """
        # Extract request context
        ip_address = _get_client_ip(request) if request else None
        user_agent = ""
        if request:
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        if not correlation_id and request:
            correlation_id = getattr(request, "correlation_id", None)
            if correlation_id and isinstance(correlation_id, str):
                try:
                    correlation_id = uuid.UUID(correlation_id)
                except ValueError:
                    correlation_id = None

        audit_entry = AuditLog.objects.create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_display=actor_display,
            impersonator_id=impersonator_id,
            action=action,
            module_id=module_id,
            resource_type=resource_type,
            resource_id=resource_id,
            before_snapshot=before,
            after_snapshot=after,
            reason=reason,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            audit_class=audit_class,
            retention_policy=retention_policy,
            metadata=metadata or {},
        )

        logger.debug(
            "Audit recorded: %s on %s:%s by %s",
            action,
            resource_type,
            resource_id,
            actor_id,
        )

        return audit_entry

    @staticmethod
    def log_security(
        *,
        tenant_id: uuid.UUID,
        action: str,
        resource_type: str,
        module_id: str,
        **kwargs,
    ) -> AuditLog:
        """Convenience: log a security-class audit entry."""
        return AuditService.log(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            module_id=module_id,
            audit_class=AuditClassification.SECURITY,
            **kwargs,
        )

    @staticmethod
    def log_financial(
        *,
        tenant_id: uuid.UUID,
        action: str,
        resource_type: str,
        module_id: str,
        **kwargs,
    ) -> AuditLog:
        """Convenience: log a financial-class audit entry."""
        return AuditService.log(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            module_id=module_id,
            audit_class=AuditClassification.FINANCIAL,
            **kwargs,
        )

    @staticmethod
    def log_compliance(
        *,
        tenant_id: uuid.UUID,
        action: str,
        resource_type: str,
        module_id: str,
        **kwargs,
    ) -> AuditLog:
        """Convenience: log a compliance-class audit entry."""
        return AuditService.log(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            module_id=module_id,
            audit_class=AuditClassification.COMPLIANCE,
            **kwargs,
        )
