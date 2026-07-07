"""
Management command: create_platform_owner
Creates platform owner user + PlatformTeamMember. Idempotent.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models.profiles import PlatformTeamArea, PlatformTeamMember
from apps.accounts.services.phone import normalize_phone, validate_iranian_phone
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount


class Command(BaseCommand):
    help = "Create the platform owner user (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--phone", required=True)
        parser.add_argument("--name", required=True)

    def handle(self, *args, **options):
        phone = normalize_phone(options["phone"])
        name = options["name"]
        if not validate_iranian_phone(phone):
            raise CommandError(f"Invalid phone: {phone}")

        tenant, _ = Tenant.objects.get_or_create(
            slug="salmandyar", defaults={"name": "سالمندیار", "status": "active"},
        )

        existing = UserAccount.objects.filter(phone=phone).first()
        if existing:
            self.stdout.write(self.style.WARNING(f"Platform owner already exists: {phone}"))
            self._ensure_team_member(existing, tenant)
            self._ensure_role(tenant, existing)
            return

        person = Person.objects.create(tenant=tenant, full_name=name)
        user = UserAccount.objects.create_user(
            phone=phone, person=person, tenant=tenant, is_staff=True, is_superuser=True,
        )
        self._ensure_role(tenant, user)
        self._ensure_team_member(user, tenant)
        self.stdout.write(self.style.SUCCESS(f"Platform owner created: {name} ({phone})"))

    def _ensure_role(self, tenant, user):
        role, _ = Role.objects.get_or_create(
            tenant=tenant, slug="platform_owner",
            defaults={"name": "مالک پلتفرم", "is_system": True},
        )
        RoleAssignment.objects.get_or_create(
            tenant=tenant, user=user, role=role, defaults={"scope_type": "platform"},
        )

    def _ensure_team_member(self, user, tenant):
        if not hasattr(user, "platform_team_member"):
            person = user.person
            if not person:
                person = Person.objects.create(tenant=tenant, full_name=str(user))
            PlatformTeamMember.objects.get_or_create(
                user=user, defaults={"person": person, "team_area": PlatformTeamArea.OWNER},
            )
