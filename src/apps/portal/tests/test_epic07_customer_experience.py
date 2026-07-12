"""Epic 07 (Customer Experience and Portal Completion) — profile, care-recipient
detail, payments/invoices, reviews, settings, and cross-customer/cross-tenant
isolation for all newly added customer portal pages."""

import uuid

from apps.accounts.services.care_recipients import CareRecipientService
from apps.finance.models import FinancialDocument, FinancialDocumentStatus, FinancialDocumentType
from apps.finance.services.party_service import FinancialPartyService
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, ServiceCategory
from apps.orders.services.order_creation import create_public_order
from apps.orders.services.status_machine import approve_public_order, complete_order, start_order
from apps.reviews.services.review_submission_service import ReviewSubmissionService

from .helpers import PortalTestCase


def _make_supplier(tenant_id, category_id):
    return ServiceSupplier.objects.create(
        tenant_id=tenant_id,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        linked_entity_id=uuid.uuid4(),
        linked_entity_type="TestProfile",
        display_name="Supplier",
        status=SupplierStatus.ACTIVE,
        availability_status=AvailabilityStatus.AVAILABLE,
        verification_level=VerificationLevel.BASIC,
        service_categories=[str(category_id)],
    )


class CustomerProfileViewTest(PortalTestCase):
    def test_requires_authentication(self):
        response = self.client.get("/portal/profile/")
        self.assertEqual(response.status_code, 403)

    def test_shows_own_profile_data(self):
        self.login_as_customer()
        response = self.client.get("/portal/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.customer.display_name)

    def test_edit_get_prefills_form(self):
        self.login_as_customer()
        response = self.client.get("/portal/profile/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.customer.display_name)

    def test_edit_post_updates_profile_via_service(self):
        self.login_as_customer()
        response = self.client.post(
            "/portal/profile/edit/",
            {
                "display_name": "New Name",
                "city": "Shiraz",
                "relation_to_elder": "child",
                "preferred_contact_method": "phone",
                "notes": "",
            },
        )
        self.assertRedirects(response, "/portal/profile/")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.display_name, "New Name")
        self.assertEqual(self.customer.city, "Shiraz")

    def test_never_exposed_publicly(self):
        response = self.client.get("/portal/profile/")
        self.assertNotEqual(response.status_code, 200)


class CareRecipientDetailViewTest(PortalTestCase):
    def test_owner_can_view_detail(self):
        self.login_as_customer()
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.care_recipient.full_name)

    def test_cannot_view_another_customers_care_recipient(self):
        other_recipient = CareRecipientService.create(customer_profile=self.other_customer, full_name="Other Elder")
        self.login_as_customer()
        response = self.client.get(f"/portal/care-recipients/{other_recipient.id}/")
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_care_recipient_is_404(self):
        self.login_as_customer()
        response = self.client.get(f"/portal/care-recipients/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 404)

    def test_shows_empty_state_when_no_orders(self):
        self.login_as_customer()
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/")
        self.assertContains(response, "هنوز درخواستی برای این گیرنده خدمت ثبت نشده است")

    def test_shows_related_order(self):
        self.login_as_customer()
        order = create_public_order(
            service_category_id=self.category.id,
            description="x",
            phone="0912",
            address="addr",
            city="tehran",
            customer_profile=self.customer,
            elder_profile=self.care_recipient,
            created_by=self.customer.user,
            tenant_id=self.tenant.id,
        )
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/")
        self.assertContains(response, order.order_number)

    def test_requires_authentication(self):
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/")
        self.assertEqual(response.status_code, 403)


class CareRecipientLabelLocalizationTest(PortalTestCase):
    """Relationship/mobility/preferred-caregiver-gender are TextChoices with
    English-only verbose_names — the detail/list/wizard pages must show the
    Persian labels from CareRecipientPresentationService's label dicts, never
    the raw stored enum value."""

    def setUp(self):
        super().setUp()
        CareRecipientService.update(
            self.care_recipient,
            relationship="father",
            mobility_level="needs_assistance",
            preferred_caregiver_gender="no_preference",
        )
        self.login_as_customer()

    def test_detail_page_shows_persian_labels_not_raw_enum_values(self):
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/")
        self.assertContains(response, "پدر")
        self.assertContains(response, "نیازمند کمک")
        self.assertContains(response, "بدون ترجیح")
        self.assertNotContains(response, "father")
        self.assertNotContains(response, "needs_assistance")
        self.assertNotContains(response, "no_preference")
        self.assertNotContains(response, "Father")
        self.assertNotContains(response, "Needs Assistance")
        self.assertNotContains(response, "No Preference")

    def test_list_page_shows_persian_label_not_raw_enum_value(self):
        response = self.client.get("/portal/care-recipients/")
        self.assertContains(response, "پدر")
        self.assertNotContains(response, "father")
        self.assertNotContains(response, "Father")

    def test_wizard_page_shows_persian_label_not_raw_enum_value(self):
        response = self.client.get("/portal/requests/new/care-recipient/")
        self.assertContains(response, "پدر")
        self.assertNotContains(response, "father")
        self.assertNotContains(response, "Father")

    def test_edit_form_options_are_localized_not_raw_enum_values(self):
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/edit/")
        self.assertContains(response, "نیازمند کمک")
        self.assertNotContains(response, "Needs Assistance")
        self.assertNotContains(response, "No Preference")

    def test_unknown_relationship_value_falls_back_safely(self):
        CareRecipientService.update(self.care_recipient, relationship="future_val")
        response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/")
        self.assertEqual(response.status_code, 200)


class CustomerPaymentsViewTest(PortalTestCase):
    def _invoice_for(self, *, order, customer, tenant):
        payer = FinancialPartyService.resolve_party_for_customer(customer)
        platform = FinancialPartyService.resolve_platform_party(tenant)
        return FinancialDocument.objects.create(
            tenant_id=tenant.id,
            document_type=FinancialDocumentType.INVOICE,
            order=order,
            issuer_party=platform,
            payer_party=payer,
            status=FinancialDocumentStatus.ISSUED,
            total_amount="1000000",
        )

    def test_requires_authentication(self):
        response = self.client.get("/portal/payments/")
        self.assertEqual(response.status_code, 403)

    def test_shows_own_invoice(self):
        order = create_public_order(
            service_category_id=self.category.id,
            description="x",
            phone="0912",
            address="addr",
            city="tehran",
            customer_profile=self.customer,
            elder_profile=self.care_recipient,
            created_by=self.customer.user,
            tenant_id=self.tenant.id,
        )
        self._invoice_for(order=order, customer=self.customer, tenant=self.tenant)
        self.login_as_customer()
        response = self.client.get("/portal/payments/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)

    def test_never_shows_another_customers_invoice(self):
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        other_order = create_public_order(
            service_category_id=other_category.id,
            description="x",
            phone="0912",
            address="addr",
            city="tehran",
            customer_profile=self.other_customer,
            elder_profile=CareRecipientService.create(customer_profile=self.other_customer, full_name="Other"),
            created_by=self.other_customer.user,
            tenant_id=self.other_tenant.id,
        )
        self._invoice_for(order=other_order, customer=self.other_customer, tenant=self.other_tenant)
        self.login_as_customer()
        response = self.client.get("/portal/payments/")
        self.assertNotContains(response, other_order.order_number)

    def test_empty_state_when_no_invoices(self):
        self.login_as_customer()
        response = self.client.get("/portal/payments/")
        self.assertContains(response, "هنوز فاکتوری برای شما صادر نشده است")


class CustomerReviewsViewTest(PortalTestCase):
    def _complete_order(self, *, customer, elder_profile, tenant_id, category_id=None):
        category_id = category_id or self.category.id
        supplier = _make_supplier(tenant_id, category_id)
        order = create_public_order(
            service_category_id=category_id,
            description="x",
            phone="0912",
            address="addr",
            city="tehran",
            customer_profile=customer,
            elder_profile=elder_profile,
            created_by=customer.user,
            tenant_id=tenant_id,
        )
        approve_public_order(order_id=order.id, reviewed_by=customer.user, assigned_supplier=supplier)
        start_order(order_id=order.id, changed_by=customer.user)
        return complete_order(order_id=order.id, changed_by=customer.user)

    def test_requires_authentication(self):
        response = self.client.get("/portal/reviews/")
        self.assertEqual(response.status_code, 403)

    def test_empty_state_when_no_reviews(self):
        self.login_as_customer()
        response = self.client.get("/portal/reviews/")
        self.assertContains(response, "هنوز نظری ثبت نکرده‌اید")

    def test_shows_own_review(self):
        order = self._complete_order(
            customer=self.customer, elder_profile=self.care_recipient, tenant_id=self.tenant.id
        )
        ReviewSubmissionService.submit_review(
            order=order,
            reviewer_person_id=self.customer.person_id,
            dimension_scores={"QUALITY": 5, "PUNCTUALITY": 4, "PROFESSIONALISM": 5, "COMMUNICATION": 4},
            written_text="عالی بود",
        )
        self.login_as_customer()
        response = self.client.get("/portal/reviews/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)

    def test_never_shows_another_customers_review(self):
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        other_elder = CareRecipientService.create(customer_profile=self.other_customer, full_name="Other")
        other_order = self._complete_order(
            customer=self.other_customer,
            elder_profile=other_elder,
            tenant_id=self.other_tenant.id,
            category_id=other_category.id,
        )
        ReviewSubmissionService.submit_review(
            order=other_order,
            reviewer_person_id=self.other_customer.person_id,
            dimension_scores={"QUALITY": 3, "PUNCTUALITY": 3, "PROFESSIONALISM": 3, "COMMUNICATION": 3},
        )
        self.login_as_customer()
        response = self.client.get("/portal/reviews/")
        self.assertNotContains(response, other_order.order_number)


class ReviewSubmitViewTest(PortalTestCase):
    def setUp(self):
        super().setUp()
        supplier = _make_supplier(self.tenant.id, self.category.id)
        order = create_public_order(
            service_category_id=self.category.id,
            description="x",
            phone="0912",
            address="addr",
            city="tehran",
            customer_profile=self.customer,
            elder_profile=self.care_recipient,
            created_by=self.customer.user,
            tenant_id=self.tenant.id,
        )
        approve_public_order(order_id=order.id, reviewed_by=self.customer.user, assigned_supplier=supplier)
        start_order(order_id=order.id, changed_by=self.customer.user)
        self.completed_order = complete_order(order_id=order.id, changed_by=self.customer.user)

    def test_owner_can_submit_review(self):
        self.login_as_customer()
        response = self.client.post(
            f"/portal/requests/{self.completed_order.id}/review/",
            {
                "quality": 5,
                "punctuality": 5,
                "professionalism": 5,
                "communication": 5,
                "written_text": "خوب بود",
            },
        )
        self.assertRedirects(response, f"/portal/requests/{self.completed_order.id}/")
        self.assertTrue(
            ReviewSubmissionService.list_for_reviewer(
                tenant_id=self.tenant.id,
                reviewer_person_id=self.customer.person_id,
            ).exists()
        )

    def test_another_customers_order_is_404(self):
        self.login_as_customer()
        other_category = ServiceCategory.objects.create(
            tenant=self.other_tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        other_elder = CareRecipientService.create(customer_profile=self.other_customer, full_name="Other")
        other_order = create_public_order(
            service_category_id=other_category.id,
            description="x",
            phone="0912",
            address="addr",
            city="tehran",
            customer_profile=self.other_customer,
            elder_profile=other_elder,
            created_by=self.other_customer.user,
            tenant_id=self.other_tenant.id,
        )
        response = self.client.post(
            f"/portal/requests/{other_order.id}/review/",
            {
                "quality": 5,
                "punctuality": 5,
                "professionalism": 5,
                "communication": 5,
                "written_text": "",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_request_detail_shows_review_form_when_eligible(self):
        self.login_as_customer()
        response = self.client.get(f"/portal/requests/{self.completed_order.id}/")
        self.assertContains(response, "ثبت نظر")

    def test_request_detail_hides_review_form_after_review_submitted(self):
        ReviewSubmissionService.submit_review(
            order=self.completed_order,
            reviewer_person_id=self.customer.person_id,
            dimension_scores={"QUALITY": 5, "PUNCTUALITY": 5, "PROFESSIONALISM": 5, "COMMUNICATION": 5},
        )
        self.login_as_customer()
        response = self.client.get(f"/portal/requests/{self.completed_order.id}/")
        self.assertNotContains(response, "ثبت نظر")


class CustomerSettingsViewTest(PortalTestCase):
    def test_requires_authentication(self):
        response = self.client.get("/portal/settings/")
        self.assertEqual(response.status_code, 403)

    def test_shows_own_phone_and_status(self):
        self.login_as_customer()
        response = self.client.get("/portal/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.customer.phone)


class CareRecipientListNavigationTest(PortalTestCase):
    def test_list_links_to_detail_page(self):
        self.login_as_customer()
        response = self.client.get("/portal/care-recipients/")
        self.assertContains(response, f"/portal/care-recipients/{self.care_recipient.id}/")


class QueryCountRegressionTest(PortalTestCase):
    """Bounded query-count regression: creates enough rows (15 orders) that
    a per-row query (N+1) would make the count scale with row count instead
    of staying flat. Catches regressions in OrderQueryService's
    select_related("service_category") and FinancialDocumentService's
    select_related("order") — both added to fix real N+1s found while
    building this Epic's pages."""

    def setUp(self):
        super().setUp()
        self.orders = [
            create_public_order(
                service_category_id=self.category.id,
                description="x",
                phone="0912",
                address="addr",
                city="tehran",
                customer_profile=self.customer,
                elder_profile=self.care_recipient,
                created_by=self.customer.user,
                tenant_id=self.tenant.id,
            )
            for _ in range(15)
        ]
        payer = FinancialPartyService.resolve_party_for_customer(self.customer)
        platform = FinancialPartyService.resolve_platform_party(self.tenant)
        for order in self.orders[:8]:
            FinancialDocument.objects.create(
                tenant_id=self.tenant.id,
                document_type=FinancialDocumentType.INVOICE,
                order=order,
                issuer_party=platform,
                payer_party=payer,
                status=FinancialDocumentStatus.ISSUED,
                total_amount="1000000",
            )
        self.login_as_customer()

    def test_dashboard_query_count_bounded(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/portal/")
        self.assertEqual(response.status_code, 200)
        self.assertLess(len(ctx.captured_queries), 20, ctx.captured_queries)

    def test_orders_list_query_count_bounded(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/portal/requests/")
        self.assertEqual(response.status_code, 200)
        self.assertLess(len(ctx.captured_queries), 10, ctx.captured_queries)

    def test_care_recipient_detail_query_count_bounded(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(f"/portal/care-recipients/{self.care_recipient.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertLess(len(ctx.captured_queries), 10, ctx.captured_queries)

    def test_payments_query_count_bounded(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/portal/payments/")
        self.assertEqual(response.status_code, 200)
        self.assertLess(len(ctx.captured_queries), 12, ctx.captured_queries)
