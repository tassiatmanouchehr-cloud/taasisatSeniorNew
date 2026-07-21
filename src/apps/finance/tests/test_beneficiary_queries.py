"""FinancialDocumentService.list_for_beneficiary_party()/
count_by_status_for_beneficiary_party() — Sprint 2.5 (Caregiver Professional
Dashboard) invoice-summary selectors."""

from apps.finance.models import FinancialDocumentStatus
from apps.finance.services import FinancialDocumentService
from apps.finance.services.party_service import FinancialPartyService

from .helpers import FinanceTestCase


class BeneficiaryPartyQueryTest(FinanceTestCase):
    def setUp(self):
        super().setUp()
        self.party = FinancialPartyService.resolve_party_for_supplier(self.supplier)

    def test_no_documents_returns_empty(self):
        self.assertEqual(
            list(
                FinancialDocumentService.list_for_beneficiary_party(tenant_id=self.tenant.id, party_id=self.party.id),
            ),
            [],
        )
        self.assertEqual(
            FinancialDocumentService.count_by_status_for_beneficiary_party(
                tenant_id=self.tenant.id,
                party_id=self.party.id,
            ),
            {},
        )

    def test_document_appears_for_its_own_beneficiary(self):
        session = self._close_execution_session()
        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        listed = list(
            FinancialDocumentService.list_for_beneficiary_party(tenant_id=self.tenant.id, party_id=self.party.id),
        )
        self.assertEqual([d.id for d in listed], [document.id])

        counts = FinancialDocumentService.count_by_status_for_beneficiary_party(
            tenant_id=self.tenant.id,
            party_id=self.party.id,
        )
        self.assertEqual(counts, {FinancialDocumentStatus.DRAFT: 1})

    def test_another_suppliers_document_never_appears(self):
        other_supplier = self._create_supplier(display_name="Other Supplier")
        other_party = FinancialPartyService.resolve_party_for_supplier(other_supplier)
        session = self._close_execution_session()
        FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        listed = list(
            FinancialDocumentService.list_for_beneficiary_party(tenant_id=self.tenant.id, party_id=other_party.id),
        )
        self.assertEqual(listed, [])

    def test_customer_payer_party_never_appears_as_beneficiary(self):
        """The customer's own party (payer_party on the same document) must
        never be returned by the beneficiary-side selector — proves the
        two sides of the same FinancialDocument are not interchangeable."""
        payer_party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        session = self._close_execution_session()
        FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        listed = list(
            FinancialDocumentService.list_for_beneficiary_party(tenant_id=self.tenant.id, party_id=payer_party.id),
        )
        self.assertEqual(listed, [])

    def test_limit_bounds_result_set(self):
        from apps.booking.services.assignment_service import AssignmentService
        from apps.orders.models import Order, OrderSource, OrderStatus

        for _ in range(3):
            order = Order.objects.create(
                tenant=self.tenant,
                source=OrderSource.OPERATOR,
                status=OrderStatus.NEW,
                service_category=self.category,
                customer_profile=self.customer_profile,
                description="x",
                city="tehran",
                address="addr",
                phone="0912",
            )
            assignment = AssignmentService.assign(order_id=order.id, supplier=self.supplier)
            session = self._close_execution_session(supplier_assignment=assignment)
            FinancialDocumentService.create_invoice_from_execution(
                execution_session_id=session.id,
                items=self._invoice_items(),
            )

        limited = list(
            FinancialDocumentService.list_for_beneficiary_party(
                tenant_id=self.tenant.id,
                party_id=self.party.id,
                limit=2,
            ),
        )
        self.assertEqual(len(limited), 2)

    def test_cross_tenant_documents_never_leak(self):
        """Same party id filtered under a different tenant_id must return
        nothing — tenant_id is not merely a convenience filter."""
        session = self._close_execution_session()
        FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=session.id,
            items=self._invoice_items(),
        )

        listed = list(
            FinancialDocumentService.list_for_beneficiary_party(
                tenant_id=self.other_tenant.id,
                party_id=self.party.id,
            ),
        )
        self.assertEqual(listed, [])
