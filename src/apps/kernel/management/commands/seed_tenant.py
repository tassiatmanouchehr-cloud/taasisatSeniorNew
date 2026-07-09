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

# Admin portal permission keys (apps.admin_portal.permission_keys) — kept as
# raw strings here rather than importing that app: Role.permissions is a
# freeform JSON string list with no registry, and apps.kernel must not
# import a higher-layer app. Granted to platform-owner so the seeded dev
# admin can actually use /admin-portal/, not just /admin/.
ADMIN_PORTAL_PERMISSIONS = [
    "admin.portal.access",
    "admin.tenants.read",
    "admin.suppliers.read",
    "admin.orders.read",
    "admin.finance.read",
    "admin.system.read",
]

# Default system roles per the Correction Package (Canonical Actor Glossary)
DEFAULT_ROLES = [
    {"slug": "platform-owner", "name": "Platform Owner", "description": "Full platform access. Super-admin."},
    {"slug": "platform-team", "name": "Platform Team Member", "description": "Internal platform staff with delegated permissions."},
    {"slug": "organization-owner", "name": "Organization Owner", "description": "Full access within own organization."},
    {"slug": "organization-staff", "name": "Organization Staff", "description": "Staff operating inside an organization with scoped permissions."},
    {"slug": "organization-operator", "name": "Organization Operator", "description": "Dispatchers and coordinators within an organization."},
    {"slug": "independent-provider", "name": "Independent Provider", "description": "Provider acting without organization affiliation."},
    {"slug": "organization-provider", "name": "Organization Provider", "description": "Provider affiliated with an organization."},
    {"slug": "customer", "name": "Customer", "description": "Person or entity requesting/buying a service."},
    {"slug": "customer-delegate", "name": "Customer Delegate", "description": "Person acting on behalf of a customer account."},
    {"slug": "trusted-person", "name": "Trusted Person", "description": "Order-scoped person with limited, temporary visibility."},
    {"slug": "support-user", "name": "Support User", "description": "Customer support staff."},
    {"slug": "finance-user", "name": "Finance User", "description": "Financial operations staff."},
    {"slug": "compliance-user", "name": "Compliance User", "description": "Compliance and governance staff."},
    {"slug": "read-only-auditor", "name": "Read-Only Auditor", "description": "Audit access with no write permissions."},
]


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
        for role_data in DEFAULT_ROLES:
            role, role_created = Role.objects.get_or_create(
                tenant=tenant,
                slug=role_data["slug"],
                defaults={
                    "name": role_data["name"],
                    "description": role_data["description"],
                    "is_system": True,
                },
            )
            if role_created:
                roles_created += 1
            if role_data["slug"] == "platform-owner":
                platform_owner_role = role
        self.stdout.write(self.style.SUCCESS(f"Roles: {roles_created} created, {len(DEFAULT_ROLES) - roles_created} already existed"))

        # Ensure platform-owner carries admin-portal access, in seed logic
        # (not manually in shell) — a role's permissions list is additive,
        # so this is safe to re-run even if a tenant customized it later.
        missing_permissions = [p for p in ADMIN_PORTAL_PERMISSIONS if p not in platform_owner_role.permissions]
        if missing_permissions:
            platform_owner_role.permissions = [*platform_owner_role.permissions, *missing_permissions]
            platform_owner_role.save(update_fields=["permissions", "updated_at", "version"])
            self.stdout.write(self.style.SUCCESS(f"Granted admin-portal permissions to platform-owner: {missing_permissions}"))

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
            tenant=tenant, user=user, role=platform_owner_role,
            defaults={"scope_type": "platform"},
        )
        if assignment_created:
            self.stdout.write(self.style.SUCCESS(f"Assigned platform-owner role to {admin_email}"))

        self.stdout.write(self.style.SUCCESS("\nSeed complete. You can now log into /admin/ with:"))
        self.stdout.write(f"  Email: {admin_email}")
        self.stdout.write(f"  Password: {'(existing)' if not user_created else admin_password}")
