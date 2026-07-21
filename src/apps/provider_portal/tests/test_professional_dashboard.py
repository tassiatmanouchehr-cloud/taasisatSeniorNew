"""Caregiver Professional Dashboard — Sprint 2.5.

Covers work summary, financial overview, wallet movements, invoice
summary, reviews/reputation, professional statistics, privacy/ownership
boundaries, and query-count bounds.
"""

from apps.booking.services.assignment_service import AssignmentService
from apps.finance.services.document_service import FinancialDocumentService
from apps.finance.services.party_service import FinancialPartyService
from apps.orders.services.status_machine import approve_cancellation, complete_order, request_cancellation, start_order
from apps.reviews.services import ReviewModerationService, ReviewSubmissionService
from apps.wallet.services.wallet_service import WalletService
from apps.wallet.services.wallet_transaction_service import WalletTransactionService

from .helpers import ProviderPortalTestCase


class DashboardWorkSummaryTest(ProviderPortalTestCase):
    def test_upcoming_order_shown_in_work_summary(self):
        self.assign_order_to_supplier()
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(response.context["dashboard"].work_summary.upcoming_count, 1)
        self.assertContains(response, self.order.order_number)

    def test_current_order_shown_in_work_summary(self):
        self.assign_order_to_supplier()
        start_order(order_id=self.order.id)
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(response.context["dashboard"].work_summary.current_count, 1)
        self.assertEqual(response.context["dashboard"].work_summary.upcoming_count, 0)

    def test_completed_order_shown_in_work_summary(self):
        self.assign_order_to_supplier()
        start_order(order_id=self.order.id)
        complete_order(order_id=self.order.id)
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(response.context["dashboard"].work_summary.completed_count, 1)

    def test_cancelled_order_shown_in_work_summary(self):
        self.assign_order_to_supplier()
        request_cancellation(order_id=self.order.id, requested_by=None, reason="x")
        approve_cancellation(order_id=self.order.id)
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(response.context["dashboard"].work_summary.cancelled_count, 1)

    def test_another_providers_orders_never_appear_in_work_summary(self):
        AssignmentService.assign(order_id=self.order.id, supplier=self.other_supplier)
        self.login_as_provider()
        response = self.client.get("/provider/")
        dashboard = response.context["dashboard"]
        self.assertEqual(
            dashboard.work_summary.current_count
            + dashboard.work_summary.upcoming_count
            + dashboard.work_summary.completed_count
            + dashboard.work_summary.cancelled_count,
            0,
        )
        self.assertNotContains(response, self.order.order_number)

    def test_cross_tenant_orders_never_appear_in_work_summary(self):
        self.assign_cross_tenant_order_to_supplier()
        self.client.force_login(self.other_tenant_provider_user)
        response = self.client.get("/provider/")
        # own-tenant dashboard shows their own order (assigned in setUp helper? none here) — assert no leakage of tenant A's order
        self.assertNotContains(response, self.order.order_number)


class DashboardFinancialOverviewTest(ProviderPortalTestCase):
    def test_no_wallet_shows_empty_state(self):
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertFalse(response.context["dashboard"].financial_overview.has_wallet)
        self.assertContains(response, "هنوز کیف پولی")

    def test_own_wallet_balance_and_movements_shown(self):
        party = FinancialPartyService.resolve_party_for_supplier(self.supplier)
        wallet = WalletService.create_wallet(party=party)
        WalletTransactionService.credit(wallet_id=wallet.id, amount="150000", reason="پرداخت سفارش")

        self.login_as_provider()
        response = self.client.get("/provider/")
        overview = response.context["dashboard"].financial_overview
        self.assertTrue(overview.has_wallet)
        self.assertEqual(len(overview.recent_movements), 1)
        self.assertContains(response, "150,000")

    def test_another_providers_wallet_never_appears(self):
        other_party = FinancialPartyService.resolve_party_for_supplier(self.other_supplier)
        other_wallet = WalletService.create_wallet(party=other_party)
        WalletTransactionService.credit(wallet_id=other_wallet.id, amount="999999", reason="متعلق به دیگری")

        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertFalse(response.context["dashboard"].financial_overview.has_wallet)
        self.assertNotContains(response, "999,999")

    def test_bonus_penalty_note_documents_the_gap(self):
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertTrue(response.context["dashboard"].financial_overview.bonus_penalty_note)


class DashboardInvoiceSummaryTest(ProviderPortalTestCase):
    def _close_and_invoice(self, *, order=None, supplier_assignment=None):
        from apps.execution.services.session_service import ExecutionService

        supplier_assignment = supplier_assignment or AssignmentService.assign(
            order_id=(order or self.order).id,
            supplier=self.supplier,
        )
        session = ExecutionService.create_session(supplier_assignment=supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        session = ExecutionService.close_session(session_id=session.id)
        return FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=[{"item_type": "SERVICE", "description": "Visit", "quantity": 1, "unit_price": "500000"}],
        )

    def test_own_invoice_appears_in_summary(self):
        self._close_and_invoice()
        self.login_as_provider()
        response = self.client.get("/provider/")
        summary = response.context["dashboard"].invoice_summary
        self.assertEqual(len(summary.recent_invoices), 1)
        self.assertContains(response, "500,000")

    def test_another_providers_invoice_never_appears(self):
        from apps.execution.services.session_service import ExecutionService

        order = self.order
        assignment = AssignmentService.assign(order_id=order.id, supplier=self.other_supplier)
        session = ExecutionService.create_session(supplier_assignment=assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        session = ExecutionService.close_session(session_id=session.id)
        FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=[{"item_type": "SERVICE", "description": "Visit", "quantity": 1, "unit_price": "777000"}],
        )

        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(len(response.context["dashboard"].invoice_summary.recent_invoices), 0)
        self.assertNotContains(response, "777,000")


class DashboardReputationTest(ProviderPortalTestCase):
    def _submit_and_approve_review(self, *, order=None, supplier_assignment=None):
        order = order or self.order
        supplier_assignment = supplier_assignment or self.supplier_assignment
        from apps.execution.services.session_service import ExecutionService

        session = ExecutionService.create_session(supplier_assignment=supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        ExecutionService.close_session(session_id=session.id)
        order.refresh_from_db()
        review = ReviewSubmissionService.submit_review(
            order=order,
            reviewer_person_id=self.customer.person_id,
            dimension_scores={"QUALITY": 5, "PUNCTUALITY": 5, "PROFESSIONALISM": 5, "COMMUNICATION": 5},
        )
        return ReviewModerationService.approve_review(review.id)

    def test_own_approved_review_appears(self):
        self.supplier_assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
        self.order.refresh_from_db()
        self._submit_and_approve_review()
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(len(response.context["dashboard"].reputation.recent_reviews), 1)

    def test_another_providers_review_never_appears(self):
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.other_supplier)
        self.order.refresh_from_db()
        self._submit_and_approve_review(order=self.order, supplier_assignment=assignment)
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(len(response.context["dashboard"].reputation.recent_reviews), 0)


class DashboardStatisticsTest(ProviderPortalTestCase):
    def test_statistics_reflect_own_skills_and_credentials(self):
        from apps.accounts.services.caregiver_professional_profile_service import CaregiverSkillService

        caregiver = self.provider_user.caregiver_profile
        CaregiverSkillService.add_skill(caregiver, name="مراقبت پایه")

        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(response.context["dashboard"].statistics.visible_skill_count, 1)

    def test_hidden_skill_not_counted(self):
        from apps.accounts.services.caregiver_professional_profile_service import CaregiverSkillService

        caregiver = self.provider_user.caregiver_profile
        skill = CaregiverSkillService.add_skill(caregiver, name="مراقبت پایه")
        CaregiverSkillService.toggle_visibility(caregiver, skill_id=skill.id)

        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertEqual(response.context["dashboard"].statistics.visible_skill_count, 0)


class DashboardAccessControlTest(ProviderPortalTestCase):
    def test_customer_cannot_access_dashboard(self):
        self.client.force_login(self.customer.user)
        response = self.client.get("/provider/")
        self.assertEqual(response.status_code, 403)

    def test_unrelated_organization_user_cannot_access_dashboard(self):
        import uuid

        from apps.kernel.models import Person, UserAccount

        person = Person.objects.create(tenant=self.tenant, full_name="Org User")
        org_user = UserAccount.objects.create_user(
            phone=f"0912{uuid.uuid4().hex[:7]}",
            person=person,
            tenant=self.tenant,
        )
        self.client.force_login(org_user)
        response = self.client.get("/provider/")
        self.assertEqual(response.status_code, 403)

    def test_each_provider_sees_only_their_own_dashboard(self):
        self.assign_order_to_supplier()
        self.client.force_login(self.other_provider_user)
        response = self.client.get("/provider/")
        self.assertEqual(response.context["dashboard"].work_summary.upcoming_count, 0)
        self.assertNotContains(response, self.order.order_number)

    def test_cross_tenant_provider_sees_only_their_own_tenant(self):
        self.assign_cross_tenant_order_to_supplier()
        self.login_as_provider()
        response = self.client.get("/provider/")
        self.assertNotContains(response, self.other_tenant_order.order_number)


class DashboardReadOnlyTest(ProviderPortalTestCase):
    def test_dashboard_get_mutates_nothing(self):
        from apps.orders.models import Order, OrderStatusHistory
        from apps.wallet.models import Wallet, WalletTransaction

        self.assign_order_to_supplier()
        self.login_as_provider()

        order_count_before = Order.objects.count()
        history_count_before = OrderStatusHistory.objects.count()
        wallet_count_before = Wallet.objects.count()
        transaction_count_before = WalletTransaction.objects.count()

        self.client.get("/provider/")

        self.assertEqual(Order.objects.count(), order_count_before)
        self.assertEqual(OrderStatusHistory.objects.count(), history_count_before)
        self.assertEqual(Wallet.objects.count(), wallet_count_before)
        self.assertEqual(WalletTransaction.objects.count(), transaction_count_before)


class DashboardQueryCountTest(ProviderPortalTestCase):
    def test_empty_dashboard_query_count_bounded(self):
        self.login_as_provider()
        with self.assertNumQueries(31):
            self.client.get("/provider/")

    def test_populated_dashboard_query_count_bounded(self):
        """One assigned+started order, 5 wallet movements: the query count
        must stay close to the empty-dashboard baseline (fixed-cost
        section queries), never grow per row — proven by asserting the
        same fixed count regardless of how many wallet transactions exist
        (5 transactions still fit inside one bounded, sliced query)."""
        self.assign_order_to_supplier()
        start_order(order_id=self.order.id)

        party = FinancialPartyService.resolve_party_for_supplier(self.supplier)
        wallet = WalletService.create_wallet(party=party)
        for i in range(5):
            WalletTransactionService.credit(wallet_id=wallet.id, amount=str(1000 + i), reason=f"m{i}")

        self.login_as_provider()
        with self.assertNumQueries(30):
            self.client.get("/provider/")

    def test_many_wallet_movements_do_not_grow_query_count(self):
        """20 wallet transactions must still cost the same fixed 30 queries
        as 5 did above — the recent-movements list is a single, sliced
        query ([:10]), never one query per transaction."""
        self.assign_order_to_supplier()
        start_order(order_id=self.order.id)

        party = FinancialPartyService.resolve_party_for_supplier(self.supplier)
        wallet = WalletService.create_wallet(party=party)
        for i in range(20):
            WalletTransactionService.credit(wallet_id=wallet.id, amount=str(1000 + i), reason=f"m{i}")

        self.login_as_provider()
        with self.assertNumQueries(30):
            self.client.get("/provider/")
