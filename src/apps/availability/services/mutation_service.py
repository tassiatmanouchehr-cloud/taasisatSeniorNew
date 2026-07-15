"""
AvailabilityMutationService — Module 10 foundation.

The only code that creates/updates/removes ProviderWorkingWindow and
AvailabilityBlockedPeriod rows. Tenant is always derived from the supplier
passed in — callers never pass a separate tenant_id.

Sprint 2.4 (Caregiver Availability and Working Schedule): add_working_window()
and update_working_window() now refuse a duplicate or overlapping *active*
working window on the same day for the same supplier (Section C — "refused
or normalized explicitly"; this service refuses). A disabled window is
excluded from that check on both sides — re-enabling it, or adding a new
window over its old slot, is allowed, matching "disabled intervals do not
count as available." Blocked periods are deliberately NOT given the same
overlap refusal: apps.availability.tests.test_query_service
.AvailabilityQueryServiceTest.test_overlapping_blocked_periods_both_apply
already establishes, as pre-existing, tested repository behavior, that two
overlapping blocked periods are harmless (redundant unavailability, not a
conflict) and must keep coexisting — see ADM-020 Decision 3.

Ownership enforcement follows this app's own pre-existing convention
(get_working_window_for_supplier()/get_blocked_period_for_supplier()
resolve-then-mutate-by-id at the call site, exactly as
apps.provider_portal.views already does for remove) rather than adding a
second, parallel ownership pattern here.

Concurrency remediation (PR #9 review, 2026-07-15): _validate_no_overlap()
is a plain SELECT, and neither add_working_window() nor
update_working_window() previously locked anything before it — under
PostgreSQL's default READ COMMITTED isolation, two concurrent transactions
mutating the same supplier's schedule could both read "no conflict" before
either commits, then both insert/activate overlapping windows
(transaction.atomic guarantees each transaction is all-or-nothing, not
that concurrent transactions serialize their reads). update_working_window()
locking only the window-being-updated did not help either: a concurrent
add_working_window() touches no existing window row at all, and two
concurrent update_working_window() calls against two *different* existing
windows of the same supplier/day each lock a different row, so neither
blocks the other's overlap check.

Fixed by locking the owning ServiceSupplier row (select_for_update()) as
the first statement inside every mutation that can introduce or activate
an interval — mirrors apps.accounts.services.caregiver_gallery_service
.CaregiverGalleryService.add_item()'s existing precedent for exactly this
shape of problem (a cross-row invariant with no single-row DB constraint
to back it, the same reason CaregiverProfile is locked before checking the
gallery item count). Both add_working_window() and update_working_window()
lock the supplier row before touching any ProviderWorkingWindow row — the
same order in both methods, so two concurrent calls (whichever mutation
they perform) always contend for the same first lock, never deadlock by
acquiring supplier/window in reverse order against each other.
toggle_working_window() is unaffected in shape — it already delegates to
update_working_window(), inheriting the fix automatically. Different
suppliers never contend for the same lock: each row-lock is scoped to
exactly one ServiceSupplier id. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020's remediation note.
"""

from django.db import transaction
from django.utils import timezone

from apps.kernel.models.supplier import ServiceSupplier

from ..models import AvailabilityBlockedPeriod, BlockedPeriodReason, ProviderWorkingWindow
from .errors import AvailabilityError


class AvailabilityMutationService:
    """Creates, updates, and removes working windows and blocked periods."""

    @classmethod
    @transaction.atomic
    def add_working_window(cls, *, supplier, day_of_week, start_time, end_time, metadata=None) -> ProviderWorkingWindow:
        cls._validate_time_range(start_time, end_time)
        # Lock the owning supplier first — there is no candidate window row
        # to lock yet (it doesn't exist), so the parent is the only stable
        # row two concurrent creates can serialize on. See this module's
        # own docstring for the full race this closes.
        locked_supplier = ServiceSupplier.objects.select_for_update().get(id=supplier.id)
        cls._validate_no_overlap(
            supplier=locked_supplier, day_of_week=day_of_week, start_time=start_time, end_time=end_time,
        )

        return ProviderWorkingWindow.objects.create(
            tenant_id=locked_supplier.tenant_id,
            supplier=locked_supplier,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            metadata=metadata or {},
        )

    @classmethod
    @transaction.atomic
    def update_working_window(cls, *, window_id, start_time=None, end_time=None, is_active=None) -> ProviderWorkingWindow:
        # Resolve the owning supplier id with a plain read first (a window's
        # supplier never changes after creation), then lock the supplier
        # before locking the window row itself — the same supplier-then-
        # window acquisition order add_working_window() uses, so the two
        # methods never deadlock against each other.
        supplier_id = ProviderWorkingWindow.objects.values_list("supplier_id", flat=True).get(id=window_id)
        locked_supplier = ServiceSupplier.objects.select_for_update().get(id=supplier_id)
        window = ProviderWorkingWindow.objects.select_for_update().get(id=window_id, supplier_id=locked_supplier.id)

        new_start = start_time if start_time is not None else window.start_time
        new_end = end_time if end_time is not None else window.end_time
        new_is_active = is_active if is_active is not None else window.is_active
        cls._validate_time_range(new_start, new_end)
        if new_is_active:
            cls._validate_no_overlap(
                supplier=locked_supplier,
                day_of_week=window.day_of_week,
                start_time=new_start,
                end_time=new_end,
                exclude_id=window.id,
            )

        window.start_time = new_start
        window.end_time = new_end
        window.is_active = new_is_active
        window.save(update_fields=["start_time", "end_time", "is_active", "updated_at"])
        return window

    @classmethod
    def toggle_working_window(cls, *, window) -> ProviderWorkingWindow:
        """Enable/disable convenience wrapper around update_working_window()
        for the provider-portal toggle button — callers pass an
        already ownership-verified window (via
        AvailabilityQueryService.get_working_window_for_supplier()), the same
        pattern this app already uses for remove."""
        return cls.update_working_window(window_id=window.id, is_active=not window.is_active)

    @classmethod
    def remove_working_window(cls, *, window_id) -> None:
        ProviderWorkingWindow.objects.filter(id=window_id).delete()

    @classmethod
    @transaction.atomic
    def add_blocked_period(
        cls, *, supplier, start_at, end_at, reason=BlockedPeriodReason.OTHER, notes="", metadata=None,
    ) -> AvailabilityBlockedPeriod:
        cls._validate_datetime_range(start_at, end_at)

        return AvailabilityBlockedPeriod.objects.create(
            tenant_id=supplier.tenant_id,
            supplier=supplier,
            start_at=start_at,
            end_at=end_at,
            reason=reason,
            notes=notes,
            metadata=metadata or {},
        )

    @classmethod
    def remove_blocked_period(cls, *, blocked_period_id) -> None:
        AvailabilityBlockedPeriod.objects.filter(id=blocked_period_id).delete()

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _validate_time_range(start_time, end_time) -> None:
        if start_time >= end_time:
            raise AvailabilityError("start_time must be strictly before end_time.")

    @staticmethod
    def _validate_no_overlap(*, supplier, day_of_week, start_time, end_time, exclude_id=None) -> None:
        """Refuses a duplicate or overlapping active window on the same day
        for the same supplier — covers exact duplicates (identical start/end
        trivially overlap) and partial overlaps in one check. Disabled
        windows are excluded: they do not count as available, so they can
        neither cause nor block an overlap."""
        existing = ProviderWorkingWindow.objects.filter(
            supplier=supplier, day_of_week=day_of_week, is_active=True,
        )
        if exclude_id is not None:
            existing = existing.exclude(id=exclude_id)
        for window in existing:
            if start_time < window.end_time and window.start_time < end_time:
                raise AvailabilityError(
                    "This working window overlaps an existing active window for the same day.",
                )

    @staticmethod
    def _validate_datetime_range(start_at, end_at) -> None:
        if timezone.is_naive(start_at) or timezone.is_naive(end_at):
            raise AvailabilityError("start_at and end_at must be timezone-aware datetimes.")
        if start_at >= end_at:
            raise AvailabilityError("start_at must be strictly before end_at.")
