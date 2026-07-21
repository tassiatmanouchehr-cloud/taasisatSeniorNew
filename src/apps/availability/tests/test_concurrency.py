"""
Availability mutation concurrency — Sprint 2.4 remediation (PR #9 review).

Proves AvailabilityMutationService.add_working_window()/
update_working_window()'s supplier-row select_for_update() lock actually
serializes concurrent mutations against the same supplier's schedule — a
database-backed guarantee, not a read-before-write check. Mirrors
apps.booking.tests.test_concurrency.ConcurrentAssignmentTest exactly: needs
TransactionTestCase (real, separately committed transactions on separate
connections) since Postgres row locking cannot be observed across threads
inside TestCase's own wrapping transaction, and available_apps=all
installed apps for the same TRUNCATE-cascade reason documented there.
"""

import datetime as dt
import threading
import uuid

from django.apps import apps as django_apps
from django.db import connection
from django.test import TransactionTestCase

from apps.availability.models import ProviderWorkingWindow
from apps.availability.services.errors import AvailabilityError
from apps.availability.services.mutation_service import AvailabilityMutationService
from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)


class _ConcurrencyFixtureMixin:
    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def _create_supplier(self, *, tenant) -> ServiceSupplier:
        return ServiceSupplier.objects.create(
            tenant_id=tenant.id,
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="TestProfile",
            display_name="Test Supplier",
            status=SupplierStatus.ACTIVE,
            availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
            service_categories=[],
        )

    def _run_concurrently(self, callables):
        """Runs each zero-arg callable in its own thread, released together
        via a shared Barrier so they genuinely race, and returns
        [("ok", value) | ("error", exc), ...] in start order (not
        completion order — callers must not assume which thread "won")."""
        barrier = threading.Barrier(len(callables))
        results = [None] * len(callables)

        def _wrap(index, fn):
            try:
                barrier.wait(timeout=5)
                value = fn()
                results[index] = ("ok", value)
            except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
                results[index] = ("error", exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=_wrap, args=(i, fn)) for i, fn in enumerate(callables)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        return results


class ConcurrentCreateTest(_ConcurrencyFixtureMixin, TransactionTestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug=f"avail-concur-{uuid.uuid4().hex[:8]}",
            name="Availability Concurrency Tenant",
        )
        self.supplier = self._create_supplier(tenant=self.tenant)

    def test_concurrent_overlapping_creates_result_in_at_most_one_success(self):
        results = self._run_concurrently(
            [
                lambda: AvailabilityMutationService.add_working_window(
                    supplier=self.supplier,
                    day_of_week=0,
                    start_time=dt.time(9, 0),
                    end_time=dt.time(17, 0),
                ),
                lambda: AvailabilityMutationService.add_working_window(
                    supplier=self.supplier,
                    day_of_week=0,
                    start_time=dt.time(10, 0),
                    end_time=dt.time(18, 0),
                ),
            ]
        )
        successes = [r for status, r in results if status == "ok"]
        failures = [r for status, r in results if status == "error"]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], AvailabilityError)
        # Final database state, not just the returned exception: exactly
        # one active window exists for this supplier/day.
        self.assertEqual(
            ProviderWorkingWindow.objects.filter(supplier=self.supplier, day_of_week=0, is_active=True).count(),
            1,
        )

    def test_concurrent_exact_duplicate_creates_result_in_at_most_one_success(self):
        results = self._run_concurrently(
            [
                lambda: AvailabilityMutationService.add_working_window(
                    supplier=self.supplier,
                    day_of_week=1,
                    start_time=dt.time(8, 0),
                    end_time=dt.time(12, 0),
                ),
                lambda: AvailabilityMutationService.add_working_window(
                    supplier=self.supplier,
                    day_of_week=1,
                    start_time=dt.time(8, 0),
                    end_time=dt.time(12, 0),
                ),
            ]
        )
        successes = [r for status, r in results if status == "ok"]
        self.assertEqual(len(successes), 1)
        self.assertEqual(
            ProviderWorkingWindow.objects.filter(supplier=self.supplier, day_of_week=1, is_active=True).count(),
            1,
        )

    def test_non_overlapping_mutation_remains_possible_after_first_completes(self):
        """Proves the lock serializes, it does not permanently block: a
        second, genuinely non-overlapping mutation against the same
        supplier still succeeds once the first transaction has committed
        and released the row lock."""
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=2,
            start_time=dt.time(8, 0),
            end_time=dt.time(12, 0),
        )
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=2,
            start_time=dt.time(13, 0),
            end_time=dt.time(17, 0),
        )
        self.assertEqual(window.start_time, dt.time(13, 0))
        self.assertEqual(
            ProviderWorkingWindow.objects.filter(supplier=self.supplier, day_of_week=2, is_active=True).count(),
            2,
        )

    def test_transaction_usable_after_controlled_conflict(self):
        """A caller whose mutation was refused for overlapping can
        immediately retry with a valid, non-overlapping window in the same
        process — the refused attempt's transaction.atomic rollback leaves
        the connection/service usable, not poisoned."""
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=3,
            start_time=dt.time(8, 0),
            end_time=dt.time(12, 0),
        )
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.add_working_window(
                supplier=self.supplier,
                day_of_week=3,
                start_time=dt.time(10, 0),
                end_time=dt.time(14, 0),
            )
        retried = AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=3,
            start_time=dt.time(13, 0),
            end_time=dt.time(17, 0),
        )
        self.assertEqual(retried.start_time, dt.time(13, 0))
        self.assertEqual(
            ProviderWorkingWindow.objects.filter(supplier=self.supplier, day_of_week=3, is_active=True).count(),
            2,
        )


class ConcurrentCreateAndUpdateTest(_ConcurrencyFixtureMixin, TransactionTestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug=f"avail-concur-{uuid.uuid4().hex[:8]}",
            name="Availability Concurrency Tenant",
        )
        self.supplier = self._create_supplier(tenant=self.tenant)
        self.existing = AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=0,
            start_time=dt.time(8, 0),
            end_time=dt.time(12, 0),
        )

    def test_concurrent_create_and_update_cannot_commit_overlap(self):
        """Neither operation conflicts with the *original* state (a new
        13-17 window; retiming the existing window's end to 14:00) — the
        conflict only exists between their two *outcomes*. Locking the
        supplier before either check runs is what makes this race
        detectable at all; without it, both could read the original,
        non-conflicting state and both commit."""
        results = self._run_concurrently(
            [
                lambda: AvailabilityMutationService.add_working_window(
                    supplier=self.supplier,
                    day_of_week=0,
                    start_time=dt.time(13, 0),
                    end_time=dt.time(17, 0),
                ),
                lambda: AvailabilityMutationService.update_working_window(
                    window_id=self.existing.id,
                    end_time=dt.time(14, 0),
                ),
            ]
        )
        successes = [r for status, r in results if status == "ok"]
        failures = [r for status, r in results if status == "error"]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], AvailabilityError)

        active_windows = list(
            ProviderWorkingWindow.objects.filter(supplier=self.supplier, day_of_week=0, is_active=True),
        )
        for a in active_windows:
            for b in active_windows:
                if a.id == b.id:
                    continue
                self.assertFalse(
                    a.start_time < b.end_time and b.start_time < a.end_time,
                    f"overlap found in final DB state: {a.start_time}-{a.end_time} vs {b.start_time}-{b.end_time}",
                )


class ConcurrentToggleTest(_ConcurrencyFixtureMixin, TransactionTestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug=f"avail-concur-{uuid.uuid4().hex[:8]}",
            name="Availability Concurrency Tenant",
        )
        self.supplier = self._create_supplier(tenant=self.tenant)
        self.window_a = AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=4,
            start_time=dt.time(8, 0),
            end_time=dt.time(12, 0),
        )
        self.window_b = AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=4,
            start_time=dt.time(13, 0),
            end_time=dt.time(17, 0),
        )
        # Disable window_b, retime it while disabled (no overlap check
        # applies to a disabled window), then disable window_a too — this
        # establishes two disabled windows whose times now genuinely
        # conflict (8-12 vs 9-11), matching the established repository
        # policy that disabled/overlapping windows may coexist.
        AvailabilityMutationService.update_working_window(window_id=self.window_b.id, is_active=False)
        AvailabilityMutationService.update_working_window(
            window_id=self.window_b.id,
            start_time=dt.time(9, 0),
            end_time=dt.time(11, 0),
            is_active=False,
        )
        AvailabilityMutationService.update_working_window(window_id=self.window_a.id, is_active=False)

    def test_concurrent_enabling_of_two_conflicting_disabled_windows_yields_at_most_one_enabled(self):
        window_a = ProviderWorkingWindow.objects.get(id=self.window_a.id)
        window_b = ProviderWorkingWindow.objects.get(id=self.window_b.id)
        results = self._run_concurrently(
            [
                lambda: AvailabilityMutationService.toggle_working_window(window=window_a),
                lambda: AvailabilityMutationService.toggle_working_window(window=window_b),
            ]
        )
        successes = [r for status, r in results if status == "ok"]
        failures = [r for status, r in results if status == "error"]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], AvailabilityError)
        self.assertEqual(
            ProviderWorkingWindow.objects.filter(
                id__in=[self.window_a.id, self.window_b.id],
                is_active=True,
            ).count(),
            1,
        )

    def test_enabling_disabled_window_overlapping_active_window_is_refused(self):
        window_b = ProviderWorkingWindow.objects.get(id=self.window_b.id)
        AvailabilityMutationService.toggle_working_window(window=window_b)  # now active, 9-11

        window_a = ProviderWorkingWindow.objects.get(id=self.window_a.id)
        with self.assertRaises(AvailabilityError):
            AvailabilityMutationService.toggle_working_window(window=window_a)  # would be 8-12, overlaps 9-11

        self.assertFalse(ProviderWorkingWindow.objects.get(id=self.window_a.id).is_active)
        self.assertTrue(ProviderWorkingWindow.objects.get(id=self.window_b.id).is_active)

    def test_disabling_a_window_is_safe_and_idempotent(self):
        # window_a is already disabled (from setUp) — disabling it again
        # must not raise and must not change any other window's state.
        result = AvailabilityMutationService.update_working_window(window_id=self.window_a.id, is_active=False)
        self.assertFalse(result.is_active)
        self.assertFalse(ProviderWorkingWindow.objects.get(id=self.window_b.id).is_active)


class ConcurrentDifferentSuppliersTest(_ConcurrencyFixtureMixin, TransactionTestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            slug=f"avail-concur-{uuid.uuid4().hex[:8]}",
            name="Availability Concurrency Tenant",
        )
        self.other_tenant = Tenant.objects.create(
            slug=f"avail-concur-other-{uuid.uuid4().hex[:8]}",
            name="Other Concurrency Tenant",
        )
        self.supplier_a = self._create_supplier(tenant=self.tenant)
        self.supplier_b = self._create_supplier(tenant=self.other_tenant)

    def test_different_suppliers_do_not_block_each_other(self):
        """Both mutations target the identical day/time window — a
        per-supplier lock lets both succeed independently (the same
        interval is valid for two different suppliers simultaneously); a
        global lock would have serialized them but still let both succeed
        eventually. The real proof is in the final state: both suppliers'
        rows exist, independently correct, and never cross-contaminated."""
        results = self._run_concurrently(
            [
                lambda: AvailabilityMutationService.add_working_window(
                    supplier=self.supplier_a,
                    day_of_week=0,
                    start_time=dt.time(9, 0),
                    end_time=dt.time(17, 0),
                ),
                lambda: AvailabilityMutationService.add_working_window(
                    supplier=self.supplier_b,
                    day_of_week=0,
                    start_time=dt.time(9, 0),
                    end_time=dt.time(17, 0),
                ),
            ]
        )
        successes = [r for status, r in results if status == "ok"]
        self.assertEqual(len(successes), 2)
        self.assertEqual(
            ProviderWorkingWindow.objects.filter(supplier=self.supplier_a, is_active=True).count(),
            1,
        )
        self.assertEqual(
            ProviderWorkingWindow.objects.filter(supplier=self.supplier_b, is_active=True).count(),
            1,
        )
        # Cross-tenant isolation intact under concurrency: each window's
        # tenant_id is derived strictly from its own supplier, never
        # blended by the concurrent lock/transaction interleaving.
        self.assertEqual(ProviderWorkingWindow.objects.get(supplier=self.supplier_a).tenant_id, self.tenant.id)
        self.assertEqual(
            ProviderWorkingWindow.objects.get(supplier=self.supplier_b).tenant_id,
            self.other_tenant.id,
        )
