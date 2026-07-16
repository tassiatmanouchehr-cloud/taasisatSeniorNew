"""Phase 3 Sprint 3.1 (Company Foundation and Caregiver Management) —
the full affiliation lifecycle: join-by-code, invitation, approval,
rejection, cancellation, termination, and the concurrency/privacy
invariants across all of them.

Deliberately does not re-prove OrganizationStaffService.approve_membership()/
suspend_membership()'s own authorization shape (apps.accounts.tests
.test_organization_staff_authorization already does) or
find_organization_by_code_or_name()'s existing behavior
(apps.accounts.tests.test_profiles_v2 already does) — this file proves the
new affiliation-lifecycle functions in apps.accounts.services.affiliations."""

import threading
import uuid

from django.apps import apps as django_apps
from django.db import transaction
from django.test import TestCase, TransactionTestCase

from apps.accounts.models.profiles import (
    AffiliationStatus,
    CaregiverProfile,
    CaregiverProviderType,
    CompanyAffiliationRequest,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
    ProfileStatus,
)
from apps.accounts.services import affiliations as svc
from apps.accounts.services.errors import AccountsError
from apps.kernel.models import Person, Tenant, UserAccount


class _FixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"affil-{uuid.uuid4().hex[:8]}", name="Affiliation Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"affil-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.admin_user = self._make_user(tenant=self.tenant, phone="09150000001")
        self.organization = OrganizationProfile.objects.create(
            name="Care Co", code=f"carecode{uuid.uuid4().hex[:6]}", admin_user=self.admin_user,
            tenant=self.tenant, status=ProfileStatus.ACTIVE,
        )
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.admin_user,
            role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )

        self.other_admin_user = self._make_user(tenant=self.tenant, phone="09150000002")
        self.other_organization = OrganizationProfile.objects.create(
            name="Other Co", code=f"othercode{uuid.uuid4().hex[:6]}", admin_user=self.other_admin_user,
            tenant=self.tenant, status=ProfileStatus.ACTIVE,
        )
        OrganizationMembership.objects.create(
            organization=self.other_organization, user=self.other_admin_user,
            role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )

        self.caregiver_user, self.caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000010")

    def _make_user(self, *, tenant, phone) -> UserAccount:
        person = Person.objects.create(tenant=tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)

    def _make_caregiver(self, *, tenant, phone):
        person = Person.objects.create(tenant=tenant, full_name="Caregiver")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        caregiver = CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name="Caregiver",
        )
        return user, caregiver


class JoinByCodeTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_valid_code_creates_pending_request(self):
        req = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        self.assertEqual(req.status, AffiliationStatus.PENDING)
        self.assertEqual(req.organization, self.organization)

    def test_invalid_code_is_refused_safely(self):
        with self.assertRaises(AccountsError):
            svc.submit_join_request(caregiver_profile=self.caregiver, code="no-such-code", tenant_id=self.tenant.id)

    def test_inactive_company_code_is_refused_identically_to_invalid(self):
        self.organization.status = ProfileStatus.DRAFT
        self.organization.save(update_fields=["status"])
        with self.assertRaisesMessage(AccountsError, "Invalid company code."):
            svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)

    def test_cross_tenant_code_is_denied(self):
        with self.assertRaises(AccountsError):
            svc.submit_join_request(
                caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.other_tenant.id,
            )

    def test_duplicate_pending_request_refused(self):
        svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        with self.assertRaises(AccountsError):
            svc.submit_join_request(caregiver_profile=self.caregiver, code=self.other_organization.code, tenant_id=self.tenant.id)

    def test_duplicate_active_membership_refused(self):
        req = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        svc.approve_affiliation_request(request_id=req.id, reviewed_by=self.admin_user)
        with self.assertRaises(AccountsError):
            svc.submit_join_request(caregiver_profile=self.caregiver, code=self.other_organization.code, tenant_id=self.tenant.id)

    def test_preview_shows_only_public_safe_fields(self):
        preview = svc.preview_join_code_organization(code=self.organization.code, tenant_id=self.tenant.id)
        self.assertEqual(set(preview.keys()), {"id", "name", "city"})
        self.assertEqual(preview["name"], "Care Co")

    def test_preview_invalid_code_returns_none(self):
        self.assertIsNone(svc.preview_join_code_organization(code="bad-code", tenant_id=self.tenant.id))

    def test_cancel_own_pending_request(self):
        req = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        svc.cancel_affiliation_request(request_id=req.id, caregiver_profile=self.caregiver)
        req.refresh_from_db()
        self.assertEqual(req.status, AffiliationStatus.CANCELLED)

    def test_cannot_cancel_another_caregivers_request(self):
        req = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        _, other_caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000011")
        with self.assertRaises(AccountsError):
            svc.cancel_affiliation_request(request_id=req.id, caregiver_profile=other_caregiver)


class ApprovalRejectionTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.request = svc.submit_join_request(
            caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id,
        )

    def test_approve_activates_membership_and_affiliates_caregiver(self):
        svc.approve_affiliation_request(request_id=self.request.id, reviewed_by=self.admin_user)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.provider_type, CaregiverProviderType.ORGANIZATION_AFFILIATED)
        membership = OrganizationMembership.objects.get(organization=self.organization, user=self.caregiver_user)
        self.assertEqual(membership.status, OrgMembershipStatus.ACTIVE)
        self.assertIsNotNone(membership.joined_at)

    def test_reject_keeps_caregiver_independent(self):
        svc.reject_affiliation_request(request_id=self.request.id, reviewed_by=self.admin_user)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.provider_type, CaregiverProviderType.INDEPENDENT)

    def test_rejoin_after_termination_reactivates_same_row(self):
        svc.approve_affiliation_request(request_id=self.request.id, reviewed_by=self.admin_user)
        membership = OrganizationMembership.objects.get(organization=self.organization, user=self.caregiver_user)
        svc.terminate_membership(membership_id=membership.id, terminated_by=self.admin_user)

        second_request = svc.submit_join_request(
            caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id,
        )
        svc.approve_affiliation_request(request_id=second_request.id, reviewed_by=self.admin_user)

        self.assertEqual(
            OrganizationMembership.objects.filter(organization=self.organization, user=self.caregiver_user).count(), 1,
        )
        membership.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.ACTIVE)
        self.assertIsNone(membership.terminated_at)


class InvitationTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_invite_creates_pending_membership(self):
        membership = svc.invite_caregiver(
            organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user,
        )
        self.assertEqual(membership.status, OrgMembershipStatus.PENDING)
        self.assertEqual(membership.invited_by, self.admin_user)

    def test_invite_unknown_phone_refused(self):
        with self.assertRaises(AccountsError):
            svc.invite_caregiver(organization=self.organization, caregiver_phone="09199999999", invited_by=self.admin_user)

    def test_accept_invitation_activates_and_affiliates(self):
        membership = svc.invite_caregiver(
            organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user,
        )
        svc.accept_invitation(membership_id=membership.id, caregiver_profile=self.caregiver)
        membership.refresh_from_db()
        self.caregiver.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.ACTIVE)
        self.assertEqual(self.caregiver.provider_type, CaregiverProviderType.ORGANIZATION_AFFILIATED)

    def test_decline_invitation_leaves_caregiver_independent(self):
        membership = svc.invite_caregiver(
            organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user,
        )
        svc.decline_invitation(membership_id=membership.id, caregiver_profile=self.caregiver)
        membership.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.REMOVED)
        self.assertEqual(membership.termination_reason, "Invitation declined by caregiver.")

    def test_other_caregiver_cannot_accept_invitation(self):
        membership = svc.invite_caregiver(
            organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user,
        )
        _, other_caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000012")
        with self.assertRaises(AccountsError):
            svc.accept_invitation(membership_id=membership.id, caregiver_profile=other_caregiver)

    def test_other_caregiver_cannot_decline_invitation(self):
        membership = svc.invite_caregiver(
            organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user,
        )
        _, other_caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000013")
        with self.assertRaises(AccountsError):
            svc.decline_invitation(membership_id=membership.id, caregiver_profile=other_caregiver)

    def test_company_cancels_own_invitation(self):
        membership = svc.invite_caregiver(
            organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user,
        )
        svc.cancel_invitation(membership_id=membership.id, cancelled_by=self.admin_user)
        membership.refresh_from_db()
        self.assertEqual(membership.status, OrgMembershipStatus.REMOVED)

    def test_invite_when_already_actively_affiliated_elsewhere_refused(self):
        req = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        svc.approve_affiliation_request(request_id=req.id, reviewed_by=self.admin_user)
        with self.assertRaises(AccountsError):
            svc.invite_caregiver(
                organization=self.other_organization, caregiver_phone=self.caregiver.phone, invited_by=self.other_admin_user,
            )


class TerminationTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        req = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        svc.approve_affiliation_request(request_id=req.id, reviewed_by=self.admin_user)
        self.membership = OrganizationMembership.objects.get(organization=self.organization, user=self.caregiver_user)

    def test_company_terminates_active_membership(self):
        svc.terminate_membership(membership_id=self.membership.id, terminated_by=self.admin_user, reason="No longer needed.")
        self.membership.refresh_from_db()
        self.caregiver.refresh_from_db()
        self.assertEqual(self.membership.status, OrgMembershipStatus.REMOVED)
        self.assertEqual(self.membership.termination_reason, "No longer needed.")
        self.assertIsNotNone(self.membership.terminated_at)
        self.assertEqual(self.membership.terminated_by, self.admin_user)
        self.assertEqual(self.caregiver.provider_type, CaregiverProviderType.INDEPENDENT)

    def test_caregiver_leaves_own_membership(self):
        svc.leave_organization(membership_id=self.membership.id, caregiver_profile=self.caregiver)
        self.membership.refresh_from_db()
        self.caregiver.refresh_from_db()
        self.assertEqual(self.membership.status, OrgMembershipStatus.REMOVED)
        self.assertEqual(self.membership.terminated_by, self.caregiver_user)
        self.assertEqual(self.caregiver.provider_type, CaregiverProviderType.INDEPENDENT)

    def test_other_caregiver_cannot_leave_someone_elses_membership(self):
        _, other_caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000014")
        with self.assertRaises(AccountsError):
            svc.leave_organization(membership_id=self.membership.id, caregiver_profile=other_caregiver)

    def test_cannot_terminate_non_active_membership(self):
        svc.terminate_membership(membership_id=self.membership.id, terminated_by=self.admin_user)
        with self.assertRaises(AccountsError):
            svc.terminate_membership(membership_id=self.membership.id, terminated_by=self.admin_user)

    def test_history_remains_available_after_termination(self):
        svc.terminate_membership(membership_id=self.membership.id, terminated_by=self.admin_user, reason="Ended.")
        history = svc.list_membership_history_for_caregiver(self.caregiver)
        self.assertEqual(list(history), [self.membership])
        self.assertEqual(history[0].status, OrgMembershipStatus.REMOVED)


class ScopedVisibilityTest(_FixtureMixin, TestCase):
    """Point 1/2 of Section J: each side sees only its own affiliations."""

    def setUp(self):
        self._build_fixture()

    def test_company_sees_only_its_own_pending_requests(self):
        svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        _, other_caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000015")
        svc.submit_join_request(caregiver_profile=other_caregiver, code=self.other_organization.code, tenant_id=self.tenant.id)

        own = svc.list_pending_requests_for_organization(self.organization)
        self.assertEqual({r.caregiver_profile_id for r in own}, {self.caregiver.id})

    def test_company_sees_only_its_own_pending_invitations(self):
        svc.invite_caregiver(organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user)
        _, other_caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000016")
        svc.invite_caregiver(
            organization=self.other_organization, caregiver_phone=other_caregiver.phone, invited_by=self.other_admin_user,
        )

        own = svc.list_pending_invitations_for_organization(self.organization)
        self.assertEqual({m.user_id for m in own}, {self.caregiver_user.id})

    def test_caregiver_sees_only_their_own_requests(self):
        svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        _, other_caregiver = self._make_caregiver(tenant=self.tenant, phone="09150000017")
        svc.submit_join_request(caregiver_profile=other_caregiver, code=self.organization.code, tenant_id=self.tenant.id)

        own = svc.list_affiliation_requests_for_caregiver(self.caregiver)
        self.assertEqual({r.caregiver_profile_id for r in own}, {self.caregiver.id})


class AffiliationConcurrencyTest(_FixtureMixin, TransactionTestCase):
    """Section I: simultaneous approval/termination is concurrency-safe.
    Mirrors apps.availability.tests.test_concurrency's
    TransactionTestCase + threading.Barrier pattern (real, separately
    committed transactions on separate connections — Postgres row locking
    cannot be observed across threads inside TestCase's own wrapping
    transaction); available_apps=all installed apps for the same
    TRUNCATE-cascade reason documented there."""

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self._build_fixture()

    def test_simultaneous_approve_and_reject_only_one_wins(self):
        req = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        barrier = threading.Barrier(2)
        results = {}

        def approve():
            try:
                barrier.wait(timeout=5)
                svc.approve_affiliation_request(request_id=req.id, reviewed_by=self.admin_user)
                results["approve"] = "ok"
            except Exception as exc:  # noqa: BLE001
                results["approve"] = type(exc).__name__
            finally:
                transaction.get_connection().close()

        def reject():
            try:
                barrier.wait(timeout=5)
                svc.reject_affiliation_request(request_id=req.id, reviewed_by=self.admin_user)
                results["reject"] = "ok"
            except Exception as exc:  # noqa: BLE001
                results["reject"] = type(exc).__name__
            finally:
                transaction.get_connection().close()

        t1 = threading.Thread(target=approve)
        t2 = threading.Thread(target=reject)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        req.refresh_from_db()
        # Exactly one of the two transitions committed — the row-locked
        # select_for_update() + PENDING-only guard means whichever thread's
        # transaction commits second sees the row already non-PENDING and
        # raises, never silently double-applies.
        self.assertIn(req.status, {AffiliationStatus.APPROVED, AffiliationStatus.REJECTED})
        outcomes = list(results.values())
        self.assertEqual(outcomes.count("ok"), 1)
        self.assertEqual(outcomes.count("AccountsError"), 1)

    def test_simultaneous_accept_and_cancel_only_one_wins(self):
        membership = svc.invite_caregiver(
            organization=self.organization, caregiver_phone=self.caregiver.phone, invited_by=self.admin_user,
        )
        barrier = threading.Barrier(2)
        results = {}

        def accept():
            try:
                barrier.wait(timeout=5)
                svc.accept_invitation(membership_id=membership.id, caregiver_profile=self.caregiver)
                results["accept"] = "ok"
            except Exception as exc:  # noqa: BLE001
                results["accept"] = type(exc).__name__
            finally:
                transaction.get_connection().close()

        def cancel():
            try:
                barrier.wait(timeout=5)
                svc.cancel_invitation(membership_id=membership.id, cancelled_by=self.admin_user)
                results["cancel"] = "ok"
            except Exception as exc:  # noqa: BLE001
                results["cancel"] = type(exc).__name__
            finally:
                transaction.get_connection().close()

        t1 = threading.Thread(target=accept)
        t2 = threading.Thread(target=cancel)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        membership.refresh_from_db()
        self.assertIn(membership.status, {OrgMembershipStatus.ACTIVE, OrgMembershipStatus.REMOVED})
        outcomes = list(results.values())
        self.assertEqual(outcomes.count("ok"), 1)
        self.assertEqual(outcomes.count("AccountsError"), 1)

    def test_duplicate_active_membership_not_creatable_under_race(self):
        """Two organizations simultaneously try to activate the same
        caregiver — the row lock inside each approval and the
        _assert_no_active_membership() check mean at most one can win."""
        req_a = svc.submit_join_request(caregiver_profile=self.caregiver, code=self.organization.code, tenant_id=self.tenant.id)
        # A second, independent request row for the other organization —
        # bypassing submit_join_request()'s own duplicate-pending guard
        # (which would otherwise refuse this at creation time) to exercise
        # the deeper, approval-time race directly.
        req_b = CompanyAffiliationRequest.objects.create(
            caregiver_profile=self.caregiver, requested_company_name_or_code=self.other_organization.code,
            organization=self.other_organization,
        )
        barrier = threading.Barrier(2)
        results = {}

        def approve_a():
            try:
                barrier.wait(timeout=5)
                svc.approve_affiliation_request(request_id=req_a.id, reviewed_by=self.admin_user)
                results["a"] = "ok"
            except Exception as exc:  # noqa: BLE001
                results["a"] = type(exc).__name__
            finally:
                transaction.get_connection().close()

        def approve_b():
            try:
                barrier.wait(timeout=5)
                svc.approve_affiliation_request(request_id=req_b.id, reviewed_by=self.other_admin_user)
                results["b"] = "ok"
            except Exception as exc:  # noqa: BLE001
                results["b"] = type(exc).__name__
            finally:
                transaction.get_connection().close()

        t1 = threading.Thread(target=approve_a)
        t2 = threading.Thread(target=approve_b)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        active_count = OrganizationMembership.objects.filter(
            user=self.caregiver_user, status=OrgMembershipStatus.ACTIVE,
        ).count()
        self.assertEqual(active_count, 1)
