"""
Management command: backfill_organization_role_assignments — Epic 04
(Enterprise Organization Isolation).

Iterates every ACTIVE, ADMIN-role OrganizationMembership and calls
OrganizationRoleSyncService.sync_for_membership() — the exact same
idempotent entry point used at runtime (membership approve/suspend), not a
parallel one-off script. Safe to re-run: sync_for_membership() is itself
idempotent (get-or-create + reactivate-in-place against the RoleAssignment
partial unique constraint), so a second run of this command creates zero
new rows.

This is the backfill that actually has a deterministic signal to work
from — unlike order eligibility (see
apps.orders.services.eligibility_service's module docstring for why no
order-eligibility backfill exists), every ACTIVE ADMIN membership
unambiguously identifies who needs a RoleAssignment. No-flag-day-lockout is
guaranteed independently of whether this command has been run yet: see
apps.booking.services.organization_assignment's module docstring for the
ownership_authorized_by fallback that covers the gap until it has.

Usage:
    python manage.py backfill_organization_role_assignments
    python manage.py backfill_organization_role_assignments --dry-run
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backfill organization-scoped RoleAssignments for existing ACTIVE ADMIN memberships (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would happen, write nothing.")

    def handle(self, *args, **options):
        from apps.accounts.models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus
        from apps.accounts.services.organization_rbac import OrganizationRoleSyncError, OrganizationRoleSyncService

        memberships = OrganizationMembership.objects.filter(
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        ).select_related("organization", "user")

        if options["dry_run"]:
            skipped = [m for m in memberships if m.organization.tenant_id is None or m.user.tenant_id is None]
            eligible = len(memberships) - len(skipped)
            self.stdout.write(
                f"[dry-run] Would sync {eligible} membership(s); would skip {len(skipped)} (missing tenant)."
            )
            for m in skipped:
                self.stdout.write(
                    self.style.WARNING(
                        f"[dry-run] Skip membership {m.id}: organization={m.organization_id} has no tenant, "
                        "or user has no tenant.",
                    )
                )
            return

        synced = 0
        skipped = 0
        errors = 0
        for membership in memberships:
            try:
                OrganizationRoleSyncService.sync_for_membership(membership)
                synced += 1
            except OrganizationRoleSyncError as exc:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skipped membership {membership.id}: {exc}"))
            except Exception as exc:  # noqa: BLE001 — reported per-row, does not abort the run
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error syncing membership {membership.id}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete: {synced} synced, {skipped} skipped (missing tenant), {errors} errors.",
            )
        )
