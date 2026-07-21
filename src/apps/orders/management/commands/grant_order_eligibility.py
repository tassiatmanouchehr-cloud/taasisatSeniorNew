"""
Management command: grant_order_eligibility — Epic 04 (Enterprise
Organization Isolation).

Thin operational wrapper around OrderEligibilityService.grant(). This is
deliberately NOT a bulk/automatic backfill policy: no signal in this
codebase identifies which organization an existing order "should" belong
to (see OrderEligibilityService's own module docstring), so this command
grants eligibility for exactly the (order, organization) pair given on the
command line — one explicit, auditable, actor-attributed grant per
invocation, calling the same service runtime code uses.

Usage:
    python manage.py grant_order_eligibility --order <order_id> --organization <organization_id>
    python manage.py grant_order_eligibility --order <order_id> --organization <organization_id> --dry-run
"""

import uuid

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant one organization eligibility for one order (explicit, no bulk policy)."

    def add_arguments(self, parser):
        parser.add_argument("--order", required=True, help="Order id (UUID).")
        parser.add_argument("--organization", required=True, help="OrganizationProfile id (UUID).")
        parser.add_argument("--dry-run", action="store_true", help="Report what would happen, write nothing.")

    def handle(self, *args, **options):
        from apps.accounts.models.profiles import OrganizationProfile
        from apps.orders.models import Order
        from apps.orders.services.eligibility_service import OrderEligibilityError, OrderEligibilityService

        try:
            order_id = uuid.UUID(options["order"])
            organization_id = uuid.UUID(options["organization"])
        except ValueError as exc:
            raise CommandError(f"Invalid UUID: {exc}")

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise CommandError(f"Order {order_id} not found.")

        try:
            organization = OrganizationProfile.objects.get(id=organization_id)
        except OrganizationProfile.DoesNotExist:
            raise CommandError(f"OrganizationProfile {organization_id} not found.")

        if options["dry_run"]:
            self.stdout.write(
                f"[dry-run] Would grant eligibility: order={order.order_number} "
                f"organization={organization.name} ({organization.id})",
            )
            return

        try:
            eligibility = OrderEligibilityService.grant(order=order, organization=organization)
        except OrderEligibilityError as exc:
            raise CommandError(str(exc))

        self.stdout.write(
            self.style.SUCCESS(
                f"Granted: order={order.order_number} organization={organization.name} status={eligibility.status}",
            )
        )
