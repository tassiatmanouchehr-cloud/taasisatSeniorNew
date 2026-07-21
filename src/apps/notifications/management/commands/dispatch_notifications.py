"""
dispatch_notifications — direct-call runner for the Module 21 dispatch
foundation.

Calls NotificationDispatchService.dispatch_pending() directly (the same
method the apps.jobs handler "notifications.dispatch_pending" calls) —
no execution logic is duplicated here. Safe to run repeatedly.

Usage:
    python manage.py dispatch_notifications
    python manage.py dispatch_notifications --limit=50
    python manage.py dispatch_notifications --tenant-id=<uuid>
    python manage.py dispatch_notifications --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.services.dispatch_service import NotificationDispatchService


class Command(BaseCommand):
    help = "Dispatch due pending notifications (Module 21 foundation runner)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Maximum number of notifications to process.")
        parser.add_argument("--tenant-id", type=str, default=None, help="Only dispatch notifications for this tenant.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many notifications are due without dispatching them.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        tenant_id = options["tenant_id"]
        dry_run = options["dry_run"]

        if dry_run:
            qs = Notification.objects.filter(status=NotificationStatus.PENDING, next_attempt_at__lte=timezone.now())
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
            due_count = qs.count()
            self.stdout.write(f"[dry-run] {due_count} notification(s) due (limit={limit})")
            return

        processed = NotificationDispatchService.dispatch_pending(tenant_id=tenant_id, limit=limit)

        sent = failed = dead_letter = 0
        for notification in processed:
            if notification.status == NotificationStatus.SENT:
                sent += 1
            elif notification.status == NotificationStatus.DEAD_LETTER:
                dead_letter += 1
            else:
                failed += 1

        self.stdout.write(
            f"Processed {len(processed)} notification(s): {sent} sent, {failed} failed (will retry), "
            f"{dead_letter} dead-lettered."
        )
