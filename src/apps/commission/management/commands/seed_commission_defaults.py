"""
seed_commission_defaults — Financial Core PR-A.

Idempotently seeds the global default commission policies (Business Model
Section 7) for a tenant. Safe to run repeatedly and safe to run against a
tenant that already has a platform-owner-configured global policy — it
never overwrites an existing active PolicyVersion (see
CommissionPolicyService.seed_defaults_if_missing()).
"""

from django.core.management.base import BaseCommand, CommandError

from apps.commission.services.policy_service import CommissionPolicyService
from apps.kernel.services.tenant_service import TenantService


class Command(BaseCommand):
    help = "Seed the Financial Core default commission policies (independent 20/80, affiliated 7/13/80, company-direct 7/93, goods 0/0/100) for a tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-slug",
            default=None,
            help="Tenant slug to seed. Defaults to the platform's default tenant.",
        )

    def handle(self, *args, **options):
        tenant_slug = options.get("tenant_slug")
        tenant = TenantService.get_tenant_by_slug(tenant_slug) if tenant_slug else TenantService.get_default_tenant()
        if tenant is None:
            raise CommandError(f"Tenant not found (slug={tenant_slug!r}).")

        version = CommissionPolicyService.seed_defaults_if_missing(tenant_id=tenant.id)
        if version is None:
            self.stdout.write(
                self.style.WARNING(
                    f"Tenant {tenant.slug!r} already has an active global commission policy — nothing changed.",
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded global commission defaults for tenant {tenant.slug!r} "
                f"(PolicyVersion {version.id}, version {version.version_number}).",
            )
        )
