"""
Management command: seed_auth_roles

Creates the minimum required roles for the real default tenant.
Idempotent — safe to run multiple times.

Epic 05 (Permission-Key Registry & Authorization Hardening): the role
list now comes from apps.kernel.role_catalog.DEFAULT_TENANT_ROLES — the
shared catalog both this command and apps.kernel.management.commands
.seed_tenant consume, replacing what used to be an inline list defined
only here. Permission lists are merged additively on every run (mirrors
seed_tenant's own missing_permissions pattern) — a role that already
existed before a permission key was added to the catalog still ends up
with it, without ever removing a tenant-customized addition. See
apps.kernel.role_catalog's own module docstring for why this command's
role set and seed_tenant's remain two distinct catalogs rather than one
merged/renamed taxonomy.

Usage:
    python manage.py seed_auth_roles
"""

from django.core.management.base import BaseCommand

from apps.kernel.models import Role, Tenant
from apps.kernel.role_catalog import DEFAULT_TENANT_ROLES


class Command(BaseCommand):
    help = "Seed the minimum required auth roles (idempotent)."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar",
            defaults={"name": "سالمندیار", "status": "active"},
        )

        created_count = 0
        for role_def in DEFAULT_TENANT_ROLES:
            role, created = Role.objects.get_or_create(
                tenant=tenant,
                slug=role_def.slug,
                defaults={
                    "name": role_def.name,
                    "is_system": role_def.is_system,
                    "permissions": list(role_def.permissions),
                },
            )
            if created:
                created_count += 1
            elif role_def.permissions:
                missing = [key for key in role_def.permissions if key not in role.permissions]
                if missing:
                    role.permissions = [*role.permissions, *missing]
                    role.save(update_fields=["permissions", "updated_at", "version"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Roles seeded: {created_count} created, "
                f"{len(DEFAULT_TENANT_ROLES) - created_count} already existed."
            )
        )
