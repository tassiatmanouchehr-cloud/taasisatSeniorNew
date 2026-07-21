"""
Management command to seed a development tenant with default roles.

Creates:
- A development tenant (slug='dev')
- A Person for the superuser
- A superuser UserAccount
- Default platform roles (system roles)

Idempotent: running twice does not duplicate data.

Usage:
    python manage.py seed_tenant
    python manage.py seed_tenant --tenant-slug=production --tenant-name="Production Tenant"
"""

from django.core.management.base import BaseCommand

from apps.kernel.models import Person, Role, RoleAssignment, Tenant, TenantStatus, UserAccount
from apps.kernel.role_catalog import DEV_BOOTSTRAP_ROLES

# Epic 05 (Permission-Key Registry & Authorization Hardening): the role
# list (including platform-owner's admin-portal permissions) now comes
# from apps.kernel.role_catalog.DEV_BOOTSTRAP_ROLES — the shared catalog
# this command and apps.accounts.management.commands.seed_auth_roles both
# consume, replacing what used to be two separate inline lists (one of
# them, ADMIN_PORTAL_PERMISSIONS, was previously defined here as raw
# strings specifically to avoid apps.kernel importing apps.admin_portal —
# now sourced from apps.kernel.permissions.keys instead, itself
# kernel-owned, so no import direction concern). See that module's own
# docstring for why this catalog and seed_auth_roles's remain two
# distinct role sets rather than one merged/renamed taxonomy.


class Command(BaseCommand):
    help = "Seed a development tenant with default roles and a superuser."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-slug",
            type=str,
            default="dev",
            help="Slug for the tenant (default: dev)",
        )
        parser.add_argument(
            "--tenant-name",
            type=str,
            default="Development Tenant",
            help="Name for the tenant (default: Development Tenant)",
        )
        parser.add_argument(
            "--admin-email",
            type=str,
            default="admin@marketplace.local",
            help="Email for the superuser (default: admin@marketplace.local)",
        )
        parser.add_argument(
            "--admin-password",
            type=str,
            default="admin123456",
            help="Password for the superuser (default: admin123456)",
        )

    def handle(self, *args, **options):
        tenant_slug = options["tenant_slug"]
        tenant_name = options["tenant_name"]
        admin_email = options["admin_email"]
        admin_password = options["admin_password"]

        # 1. Create or get tenant
        tenant, created = Tenant.objects.get_or_create(
            slug=tenant_slug,
            defaults={
                "name": tenant_name,
                "status": TenantStatus.ACTIVE,
                "settings": {"marketplace_model": "hybrid"},
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created tenant: {tenant.name} ({tenant.slug})"))
        else:
            self.stdout.write(f"Tenant already exists: {tenant.name} ({tenant.slug})")

        # 2. Create default roles
        roles_created = 0
        platform_owner_role = None
        for role_def in DEV_BOOTSTRAP_ROLES:
            role, role_created = Role.objects.get_or_create(
                tenant=tenant,
                slug=role_def.slug,
                defaults={
                    "name": role_def.name,
                    "description": role_def.description,
                    "is_system": role_def.is_system,
                    "permissions": list(role_def.permissions),
                },
            )
            if role_created:
                roles_created += 1
            elif role_def.permissions:
                # Additive merge — a role's permissions list is additive,
                # so this is safe to re-run even if a tenant customized it
                # later (mirrors seed_auth_roles.py's identical pattern).
                missing = [key for key in role_def.permissions if key not in role.permissions]
                if missing:
                    role.permissions = [*role.permissions, *missing]
                    role.save(update_fields=["permissions", "updated_at", "version"])
                    self.stdout.write(self.style.SUCCESS(f"Granted permissions to {role.slug}: {missing}"))
            if role_def.slug == "platform-owner":
                platform_owner_role = role
        self.stdout.write(
            self.style.SUCCESS(
                f"Roles: {roles_created} created, {len(DEV_BOOTSTRAP_ROLES) - roles_created} already existed",
            )
        )

        # 3. Create Person + superuser
        person, person_created = Person.objects.get_or_create(
            tenant=tenant,
            full_name="Platform Administrator",
            defaults={"metadata": {"seeded": True}},
        )
        if person_created:
            self.stdout.write(self.style.SUCCESS(f"Created person: {person.full_name}"))

        user, user_created = UserAccount.objects.get_or_create(
            email=admin_email,
            defaults={
                "person": person,
                "tenant": tenant,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if user_created:
            user.set_password(admin_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created superuser: {admin_email}"))
        else:
            self.stdout.write(f"Superuser already exists: {admin_email}")

        # 4. Assign platform-owner to the seeded admin so /admin-portal/ works too
        # (is_superuser alone grants nothing under PermissionService — RBAC is fail-closed).
        _, assignment_created = RoleAssignment.objects.get_or_create(
            tenant=tenant,
            user=user,
            role=platform_owner_role,
            defaults={"scope_type": "platform"},
        )
        if assignment_created:
            self.stdout.write(self.style.SUCCESS(f"Assigned platform-owner role to {admin_email}"))

        self.stdout.write(self.style.SUCCESS("\nSeed complete. You can now log into /admin/ with:"))
        self.stdout.write(f"  Email: {admin_email}")
        self.stdout.write(f"  Password: {'(existing)' if not user_created else admin_password}")
