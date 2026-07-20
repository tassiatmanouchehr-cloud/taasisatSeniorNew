"""
Emergency management command: change the RBAC enforcement toggle
(rbac.enforcement.enabled) for a single tenant.

Approved architecture decision (RBAC Enforcement-Toggle Visibility & Audit
Remediation, 2026-07-20): this key is an emergency operational control,
not a business or admin feature. This command is the ONLY supported way
to change it — there is deliberately no Admin Portal, Django Admin,
public UI, internal application UI, or API mutation path. See
apps.kernel.services.rbac_configuration.RBACConfiguration
.set_enforcement_enabled() for the sanctioned service-layer write path
this command delegates to (all validation, tenant-isolation, audit
logging, and cache invalidation live there — this command does not
touch any model directly).

Usage:
    python manage.py set_rbac_enforcement \\
        --tenant <tenant-uuid-or-slug> --enabled true \\
        --reason "restoring enforcement after incident INC-123" \\
        --actor "ops:jane@example.com"

    python manage.py set_rbac_enforcement \\
        --tenant <tenant-uuid-or-slug> --enabled false \\
        --reason "emergency bypass for incident INC-123, approved by CTO" \\
        --actor "ops:jane@example.com" --confirm-disable
"""

import uuid

from django.core.management.base import BaseCommand, CommandError

from apps.kernel.models.tenant import Tenant
from apps.kernel.services.rbac_configuration import RBACConfiguration, RBACConfigurationError

TRUE_VALUES = {"true", "1", "yes"}
FALSE_VALUES = {"false", "0", "no"}


class Command(BaseCommand):
    help = (
        "Emergency control: change the RBAC enforcement toggle for one tenant. "
        "The only supported write path for rbac.enforcement.enabled."
    )

    def add_arguments(self, parser):
        parser.add_argument("--tenant", required=True, help="Tenant UUID or slug.")
        parser.add_argument("--enabled", required=True, help="true|false")
        parser.add_argument("--reason", required=True, help="Mandatory operational reason for this change.")
        parser.add_argument(
            "--actor", required=True,
            help="Explicit operator identity (e.g. 'ops:jane@example.com'). Never inferred.",
        )
        parser.add_argument("--correlation-id", default=None, help="Optional correlation UUID for this operation.")
        parser.add_argument(
            "--source", default="management_command",
            help="Audit metadata: where this change originated from (default: management_command).",
        )
        parser.add_argument(
            "--confirm-disable", action="store_true",
            help="Required to disable enforcement. Disabling bypasses authorization checks platform-wide for this tenant.",
        )

    def handle(self, *args, **options):
        tenant = self._resolve_tenant(options["tenant"])
        enabled = self._parse_bool(options["enabled"])

        reason = (options["reason"] or "").strip()
        if not reason:
            raise CommandError("--reason is required and cannot be empty.")

        actor = (options["actor"] or "").strip()
        if not actor:
            raise CommandError("--actor is required and cannot be empty.")

        if not enabled and not options["confirm_disable"]:
            raise CommandError(
                "Disabling RBAC enforcement requires --confirm-disable. "
                "This bypasses authorization checks platform-wide for this tenant."
            )

        correlation_id = None
        if options["correlation_id"]:
            try:
                correlation_id = uuid.UUID(options["correlation_id"])
            except ValueError:
                raise CommandError("--correlation-id must be a valid UUID.") from None

        try:
            status = RBACConfiguration.set_enforcement_enabled(
                tenant_id=tenant.id,
                enabled=enabled,
                actor_display=actor,
                reason=reason,
                correlation_id=correlation_id,
                source=options["source"],
                operation="set_rbac_enforcement",
            )
        except RBACConfigurationError as exc:
            raise CommandError(str(exc)) from exc

        state_label = "ENABLED" if status.enabled else "DISABLED"
        self.stdout.write(self.style.SUCCESS(
            f"RBAC enforcement for tenant {tenant.slug} ({tenant.id}) is now "
            f"{state_label} (source={status.source})."
        ))
        if not status.enabled:
            self.stdout.write(self.style.WARNING(
                "WARNING: RBAC enforcement is DISABLED for this tenant. "
                "Permission checks are bypassed platform-wide until re-enabled "
                "with this same command."
            ))

    def _resolve_tenant(self, raw: str) -> Tenant:
        raw = (raw or "").strip()
        if not raw:
            raise CommandError("--tenant is required and cannot be empty.")

        try:
            tenant_uuid = uuid.UUID(raw)
        except ValueError:
            tenant_uuid = None

        if tenant_uuid is not None:
            try:
                return Tenant.objects.get(id=tenant_uuid)
            except Tenant.DoesNotExist:
                raise CommandError(f"No tenant found with id {raw!r}.") from None

        matches = list(Tenant.objects.filter(slug=raw))
        if not matches:
            raise CommandError(f"No tenant found with slug {raw!r}.")
        if len(matches) > 1:
            raise CommandError(f"Slug {raw!r} matches multiple tenants — ambiguous, pass the tenant UUID instead.")
        return matches[0]

    @staticmethod
    def _parse_bool(raw: str) -> bool:
        normalized = (raw or "").strip().lower()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
        raise CommandError(f"--enabled must be one of true|false (got {raw!r}).")
