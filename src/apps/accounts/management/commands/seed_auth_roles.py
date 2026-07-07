"""
Management command: seed_auth_roles

Creates the minimum required roles for the platform.
Idempotent — safe to run multiple times.

Usage:
    python manage.py seed_auth_roles
"""

from django.core.management.base import BaseCommand

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
    {"slug": "organization_admin", "name": "مدیر سازمان", "is_system": True},
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
            _, created = Role.objects.get_or_create(
                tenant=tenant,
                slug=role_data["slug"],
                defaults={
                    "name": role_data["name"],
                    "is_system": role_data["is_system"],
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Roles seeded: {created_count} created, "
                f"{len(ROLES) - created_count} already existed."
            )
        )
