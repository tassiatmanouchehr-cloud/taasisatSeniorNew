"""
AvailabilityQueryService — Module 10 foundation.

Pure read-side evaluation: does a supplier's configured schedule (working
windows minus blocked periods) cover an explicit, caller-supplied
[start, end) range? Deliberately takes explicit datetimes rather than an
Order — Order's own scheduling fields (scheduled_for / requested_time_window)
are not a clean range today, so this service stays decoupled from that.

Absence of any configured working window is treated conservatively as
"not available" (fail-closed) — an unconfigured schedule is unknown, not open.

Foundation scope: a requested range must fall within a single local
calendar day. Ranges spanning local midnight (e.g. an overnight shift) are
rejected with AvailabilityError rather than silently evaluated — that is
deferred to a follow-up once there's a concrete overnight-shift use case
to design correctly against.

Sprint 2.4 (Caregiver Availability and Working Schedule): evaluate() is the
one canonical, structured evaluator — is_supplier_available() is now a thin
bool-only wrapper around it, so there is exactly one evaluation
implementation, never two. This service stays supplier-keyed (never
caregiver-keyed): apps.availability sits below apps.accounts in the
dependency graph (kernel -> accounts -> orders -> ... -> availability), so
it must not know about CaregiverProfile, and a caregiver-shaped entry point
would have to live above this app, not inside it — apps.provider_portal and
apps.public_site, which already resolve their own ServiceSupplier before
ever needing an evaluation, call this evaluator directly instead of through
a duplicate caregiver-facing service. See
traceability/ARCHITECTURE_DECISION_LOG.md ADM-020 Decision 1.

get_distinct_active_days() is deliberately domain-only (a sorted tuple of
DayOfWeek ints) — the Persian display labels for those ints live in
apps.availability.models.PERSIAN_DAY_LABELS, one canonical translation
shared by every caller, not a UI concept duplicated inside this service.
"""

from dataclasses import dataclass

from django.utils import timezone

from ..models import AvailabilityBlockedPeriod, ProviderWorkingWindow
from .errors import AvailabilityError


@dataclass(frozen=True)
class AvailabilityEvaluation:
    """Structured result of AvailabilityQueryService.evaluate() — read-only,
    never persisted. `reasons` is always populated when available is False,
    empty when True."""

    available: bool
    reasons: tuple[str, ...]
    matched_window: ProviderWorkingWindow | None
    conflicting_blocked_period: AvailabilityBlockedPeriod | None
    timezone: str


class AvailabilityQueryService:
    """Evaluates supplier availability for an explicit time range."""

    @classmethod
    def evaluate(cls, *, supplier, start, end) -> AvailabilityEvaluation:
        """The one canonical, structured availability evaluator. Read-only —
        never creates, mutates, or deletes any row, and never inspects
        booking/execution state (Section E's item 6 is explicitly deferred;
        see ADM-020 Decision 2)."""
        cls._validate_range(start, end)
        tz_name = timezone.get_current_timezone_name()

        conflicting = cls._first_blocking_overlap(supplier=supplier, start=start, end=end)
        if conflicting is not None:
            return AvailabilityEvaluation(
                available=False,
                reasons=("blocked_period",),
                matched_window=None,
                conflicting_blocked_period=conflicting,
                timezone=tz_name,
            )

        matched = cls._matching_working_window(supplier=supplier, start=start, end=end)
        if matched is None:
            return AvailabilityEvaluation(
                available=False,
                reasons=("no_matching_working_window",),
                matched_window=None,
                conflicting_blocked_period=None,
                timezone=tz_name,
            )

        return AvailabilityEvaluation(
            available=True,
            reasons=(),
            matched_window=matched,
            conflicting_blocked_period=None,
            timezone=tz_name,
        )

    @classmethod
    def is_supplier_available(cls, *, supplier, start, end) -> bool:
        return cls.evaluate(supplier=supplier, start=start, end=end).available

    @classmethod
    def get_working_windows(cls, *, supplier, day_of_week=None):
        qs = ProviderWorkingWindow.objects.filter(supplier=supplier, is_active=True)
        if day_of_week is not None:
            qs = qs.filter(day_of_week=day_of_week)
        return qs

    @classmethod
    def get_distinct_active_days(cls, *, supplier) -> tuple[int, ...]:
        """Sorted, deduplicated DayOfWeek values with at least one active
        working window — the safe, summarized shape the public profile and
        the provider-portal public-summary preview both need (never exact
        start/end times). One query, independent of how many windows exist.
        Deduplicated in Python, not via queryset .distinct() — the model's
        own Meta.ordering (day_of_week, start_time) would otherwise force
        start_time into the implicit ORDER BY and silently defeat
        .distinct() on the single day_of_week column."""
        days = ProviderWorkingWindow.objects.filter(
            supplier=supplier,
            is_active=True,
        ).values_list("day_of_week", flat=True)
        return tuple(sorted(set(days)))

    @classmethod
    def get_blocked_periods(cls, *, supplier, start=None, end=None):
        qs = AvailabilityBlockedPeriod.objects.filter(supplier=supplier)
        if start is not None and end is not None:
            qs = qs.filter(start_at__lt=end, end_at__gt=start)
        return qs

    @classmethod
    def get_working_window_for_supplier(cls, *, supplier, window_id):
        """Ownership-scoped single-row lookup — Epic 02 (Marketplace Operational
        Experience), so apps.provider_portal can verify a window belongs to the
        caller before mutating it, without filtering a queryset in the view."""
        return ProviderWorkingWindow.objects.filter(supplier=supplier, id=window_id).first()

    @classmethod
    def get_blocked_period_for_supplier(cls, *, supplier, blocked_period_id):
        """Ownership-scoped single-row lookup — Epic 02, same reasoning as
        get_working_window_for_supplier()."""
        return AvailabilityBlockedPeriod.objects.filter(supplier=supplier, id=blocked_period_id).first()

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _validate_range(start, end) -> None:
        if start is None or end is None:
            raise AvailabilityError("Both start and end are required.")
        if timezone.is_naive(start) or timezone.is_naive(end):
            raise AvailabilityError("start and end must be timezone-aware datetimes.")
        if start >= end:
            raise AvailabilityError("start must be strictly before end.")

        local_start = timezone.localtime(start)
        local_end = timezone.localtime(end)
        if local_start.date() != local_end.date():
            raise AvailabilityError(
                "Requested range spans local midnight; overnight ranges are not supported yet.",
            )

    @staticmethod
    def _first_blocking_overlap(*, supplier, start, end) -> AvailabilityBlockedPeriod | None:
        return (
            AvailabilityBlockedPeriod.objects.filter(
                supplier=supplier,
                start_at__lt=end,
                end_at__gt=start,
            )
            .order_by("start_at")
            .first()
        )

    @staticmethod
    def _matching_working_window(*, supplier, start, end) -> ProviderWorkingWindow | None:
        local_start = timezone.localtime(start)
        local_end = timezone.localtime(end)
        day_of_week = local_start.weekday()

        windows = ProviderWorkingWindow.objects.filter(
            supplier=supplier,
            day_of_week=day_of_week,
            is_active=True,
        )
        for window in windows:
            if window.start_time <= local_start.time() and local_end.time() <= window.end_time:
                return window
        return None
