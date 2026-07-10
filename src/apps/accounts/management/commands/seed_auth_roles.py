"""
Management command: seed_auth_roles

Creates the minimum required roles for the platform.
Idempotent — safe to run multiple times.

Epic 04 (Enterprise Organization Isolation): organization_admin now also
carries a permissions list, merged additively on every run (mirrors
apps.kernel.management.commands.seed_tenant's own missing_permissions
pattern) — a role that already existed before this Epic's permission keys
were defined still ends up with all of them, without ever removing a
tenant-customized addition. This is also the SAME organization_admin
RoleAssignment slug apps.accounts.services.organization_rbac
.OrganizationRoleSyncService resolves/creates lazily at sync time — running
this command is not required for the sync service to work (it creates the
role itself if missing), but running it proactively keeps a fresh tenant's
role catalog populated before any membership is ever approved. See
docs/architecture/technical-debt-register.md for the known divergence
between this command and apps.kernel.management.commands.seed_tenant's own
separate, hyphenated-slug role catalog — the two are not yet reconciled
(Epic 05 territory, not this Epic's scope).

Usage:
    python manage.py seed_auth_roles
"""

from django.core.management.base import BaseCommand

from apps.accounts.services.organization_rbac import ORGANIZATION_ADMIN_PERMISSIONS
from apps.kernel.models import Role, Tenant

ROLES = [
    # Platform roles
    {"slug": "platform_owner", "name": "مالک پلتفرم", "is_system": True},
    {"slug": "platform_admin", "name": "مدیر پلتفرم", "is_system": True},
    {"slug": "platform_operator", "name": "اپراتور پلتفرم", "is_system": True},
    {"slug": "platform_support", "name": "پشتیبانی پلتفرم", "is_system": True},
    {"slug": "platform_accounting", "name": "حسابداری پلتفرم", "is_system": True},
    {"slug": "platform_security", "name": "امنیت پلتفرم", "is_system": True},
    {"slug": "platform_it", "name": "فناوری اطلاعات پلتفرم", "is_system": True},
    # Customer roles
    {"slug": "customer", "name": "مشتری / خانواده", "is_system": True},
    # Provider roles
    {"slug": "independent_caregiver", "name": "مراقب مستقل", "is_system": True},
    {"slug": "organization_caregiver", "name": "مراقب سازمانی", "is_system": True},
    # Organization roles
    {"slug": "organization_admin", "name": "مدیر سازمان", "is_system": True, "permissions": ORGANIZATION_ADMIN_PERMISSIONS},
    {"slug": "organization_operator", "name": "اپراتور سازمان", "is_system": True},
]


class Command(BaseCommand):
    help = "Seed the minimum required auth roles (idempotent)."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar",
            defaults={"name": "سالمندیار", "status": "active"},
        )

        created_count = 0
        for role_data in ROLES:
            wanted_permissions = role_data.get("permissions", [])
            role, created = Role.objects.get_or_create(
                tenant=tenant,
                slug=role_data["slug"],
                defaults={
                    "name": role_data["name"],
                    "is_system": role_data["is_system"],
                    "permissions": list(wanted_permissions),
                },
            )
            if created:
                created_count += 1
            elif wanted_permissions:
                missing = [key for key in wanted_permissions if key not in role.permissions]
                if missing:
                    role.permissions = [*role.permissions, *missing]
                    role.save(update_fields=["permissions", "updated_at", "version"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Roles seeded: {created_count} created, "
                f"{len(ROLES) - created_count} already existed."
            )
        )
