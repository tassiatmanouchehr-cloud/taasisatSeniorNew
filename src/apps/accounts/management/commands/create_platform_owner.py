"""
Management command: create_platform_owner

Creates the platform owner user (Manouchehr) with platform_owner role.
Idempotent — safe to run multiple times.

Usage:
    python manage.py create_platform_owner --phone 09121234567 --name "Manouchehr"
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services.phone import normalize_phone, validate_iranian_phone
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount


class Command(BaseCommand):
    help = "Create the platform owner user (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--phone", required=True, help="Phone number (09xxxxxxxxx)")
        parser.add_argument("--name", required=True, help="Full name")

    def handle(self, *args, **options):
        phone = normalize_phone(options["phone"])
        name = options["name"]

        if not validate_iranian_phone(phone):
            raise CommandError(f"Invalid phone number: {phone}")

        tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar",
            defaults={"name": "سالمندیار", "status": "active"},
        )

        # Check if user already exists
        existing = UserAccount.objects.filter(phone=phone).first()
        if existing:
            self.stdout.write(self.style.WARNING(
                f"Platform owner already exists: {existing.phone}"
            ))
            # Ensure role is assigned
            self._ensure_role(tenant, existing)
            return

        # Create person + user
        person = Person.objects.create(
            tenant=tenant,
            full_name=name,
        )

        user = UserAccount.objects.create_user(
            phone=phone,
            person=person,
            tenant=tenant,
            is_staff=True,
            is_superuser=True,
        )

        self._ensure_role(tenant, user)

        self.stdout.write(self.style.SUCCESS(
            f"Platform owner created: {name} ({phone})"
        ))

    def _ensure_role(self, tenant, user):
        """Ensure platform_owner role is assigned."""
        role, _ = Role.objects.get_or_create(
            tenant=tenant,
            slug="platform_owner",
            defaults={"name": "مالک پلتفرم", "is_system": True},
        )
        RoleAssignment.objects.get_or_create(
            tenant=tenant,
            user=user,
            role=role,
            defaults={"scope_type": "platform"},
        )
