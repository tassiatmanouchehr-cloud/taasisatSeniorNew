"""
Management command: reconcile_role_permissions — Epic 05 (Permission-Key
Registry & Authorization Hardening).

Operational reconciliation between the shared role catalog
(apps.kernel.role_catalog) and the actual Role rows in the database, per
tenant. Default mode is additive and non-destructive: missing canonical
permissions are added, nothing already on a role is ever removed unless
--remove-unknown is explicitly passed, and even then only permission keys
that are BOTH not part of the role's canonical set AND not a real,
registered key at all (a genuine typo/retired key) are ever removed — a
custom-but-valid permission grant (some other real, registered key a
tenant deliberately added) is never touched, destructive flag or not.

Idempotent and safe to re-run after a partial failure: each (tenant, role)
pair is reconciled independently, no single transaction spans the whole
run.

Usage:
    python manage.py reconcile_role_permissions
    python manage.py reconcile_role_permissions --dry-run
    python manage.py reconcile_role_permissions --tenant=salmandyar
    python manage.py reconcile_role_permissions --remove-unknown
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Reconcile Role.permissions against the canonical role catalog, tenant-by-tenant (additive by default)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would happen, write nothing.")
        parser.add_argument("--tenant", type=str, default=None, help="Limit to one tenant slug. Default: every tenant.")
        parser.add_argument(
            "--remove-unknown", action="store_true",
            help="Also remove permission keys that are neither canonical for the role NOR a real "
                 "registered key anywhere (a genuine typo/retired key). Never removes a valid, "
                 "registered custom addition. Off by default.",
        )

    def handle(self, *args, **options):
        from apps.kernel.models import Role, Tenant
        from apps.kernel.permissions.registry import PermissionRegistry
        from apps.kernel.role_catalog import all_role_definitions

        dry_run = options["dry_run"]
        remove_unknown = options["remove_unknown"]

        catalog_by_slug = {role_def.slug: role_def for role_def in all_role_definitions()}

        tenants = Tenant.objects.filter(slug=options["tenant"]) if options["tenant"] else Tenant.objects.all()

        totals = {"added": 0, "removed": 0, "unknown_reported": 0, "roles_checked": 0}

        for tenant in tenants:
            for role in Role.objects.filter(tenant=tenant, slug__in=catalog_by_slug.keys()):
                totals["roles_checked"] += 1
                self._reconcile_one(
                    tenant=tenant, role=role, role_def=catalog_by_slug[role.slug],
                    dry_run=dry_run, remove_unknown=remove_unknown, totals=totals,
                )

        verb = "Would reconcile" if dry_run else "Reconciled"
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: {totals['roles_checked']} role(s) checked, "
            f"{totals['added']} permission(s) added, {totals['removed']} removed, "
            f"{totals['unknown_reported']} unknown permission(s) reported.",
        ))

    def _reconcile_one(self, *, tenant, role, role_def, dry_run, remove_unknown, totals):
        from apps.kernel.permissions.registry import PermissionRegistry

        canonical = set(role_def.permissions)
        current = list(role.permissions)

        missing = [key for key in role_def.permissions if key not in current]
        unknown = [key for key in current if key not in canonical and not PermissionRegistry.exists(key)]
        custom_but_valid = [key for key in current if key not in canonical and PermissionRegistry.exists(key)]

        if unknown:
            totals["unknown_reported"] += len(unknown)
            self.stdout.write(self.style.WARNING(
                f"[{tenant.slug}/{role.slug}] unknown/unregistered permission key(s) present: {unknown}",
            ))
        if custom_but_valid:
            self.stdout.write(f"[{tenant.slug}/{role.slug}] preserving custom valid permission(s): {custom_but_valid}")

        to_remove = unknown if remove_unknown else []

        if not missing and not to_remove:
            return

        if dry_run:
            if missing:
                self.stdout.write(f"[dry-run] [{tenant.slug}/{role.slug}] would add: {missing}")
            if to_remove:
                self.stdout.write(f"[dry-run] [{tenant.slug}/{role.slug}] would remove: {to_remove}")
            totals["added"] += len(missing)
            totals["removed"] += len(to_remove)
            return

        with transaction.atomic():
            role.permissions = [key for key in current if key not in to_remove]
            role.permissions.extend(key for key in missing if key not in role.permissions)
            role.save(update_fields=["permissions", "updated_at", "version"])

        totals["added"] += len(missing)
        totals["removed"] += len(to_remove)
        if missing:
            self.stdout.write(self.style.SUCCESS(f"[{tenant.slug}/{role.slug}] added: {missing}"))
        if to_remove:
            self.stdout.write(self.style.WARNING(f"[{tenant.slug}/{role.slug}] removed: {to_remove}"))
