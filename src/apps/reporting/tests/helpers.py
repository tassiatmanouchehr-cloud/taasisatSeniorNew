"""Shared fixtures for reporting tests (not a test module itself). Builds one real,
end-to-end order -> execution -> invoice -> payment -> wallet -> review chain so
aggregation correctness can be checked against known values."""

import uuid
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models.profiles import CustomerProfile
from apps.booking.services.assignment_service import AssignmentService
from apps.execution.services.session_service import ExecutionService
from apps.finance.models import PaymentMethod
from apps.finance.services import FinancialDocumentService, FinancialPartyService, PaymentService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory
from apps.reviews.services import ReviewModerationService, ReviewSubmissionService
from apps.wallet.services import WalletService, WalletTransactionService


class ReportingTestCase(TestCase):
    """Base test case: a tenant with one full order->execution->invoice->payment->wallet->review chain."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"reporting-{uuid.uuid4().hex[:8]}", name="Reporting Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"reporting-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )

        self.customer_profile = self._create_customer(tenant=self.tenant)
        self.supplier = self._create_supplier(tenant=self.tenant)

        self.order = self._create_order(tenant=self.tenant, category=self.category, customer_profile=self.customer_profile)
        self.supplier_assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)

        self.execution_session = self._close_execution_session(self.supplier_assignment)
        self.order.refresh_from_db()

        self.document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=self.execution_session.id, items=self._invoice_items(),
        )
        self.document = FinancialDocumentService.issue_document(document_id=self.document.id)

        self.payer_party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        self.supplier_party = FinancialPartyService.resolve_party_for_supplier(self.supplier)

        self.payment = PaymentService.record_payment(
            payer_party_id=self.payer_party.id,
            receiver_party_id=self.supplier_party.id,
            amount=self.document.total_amount,
            payment_method=PaymentMethod.ONLINE,
            source_document_id=self.document.id,
        )

        self.wallet = WalletService.create_wallet(party=self.payer_party)
        WalletTransactionService.credit(wallet_id=self.wallet.id, amount=Decimal("50000"))
        self.wallet.refresh_from_db()

        self.review = ReviewSubmissionService.submit_review(
            order=self.order,
            reviewer_person_id=self.customer_profile.person_id,
            dimension_scores={"QUALITY": 5, "PUNCTUALITY": 4, "PROFESSIONALISM": 5, "COMMUNICATION": 4},
        )
        ReviewModerationService.approve_review(self.review.id)
        self.supplier.refresh_from_db()
        self.order.refresh_from_db()

    def _create_customer(self, *, tenant, display_name="Test Customer", phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(
            user=user, person=person, phone=phone, display_name=display_name,
        )

    def _create_order(self, *, tenant, category, customer_profile) -> Order:
        return Order.objects.create(
            tenant=tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=category,
            customer_profile=customer_profile,
            description="Need home care",
            city="tehran",
            address="Some address",
            phone="09120000000",
        )

    def _create_supplier(self, *, tenant=None, **kwargs) -> ServiceSupplier:
        tenant = tenant or self.tenant
        defaults = {
            "tenant_id": tenant.id,
            "supplier_type": SupplierType.INDEPENDENT_PROVIDER,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": SupplierStatus.ACTIVE,
            "availability_status": AvailabilityStatus.AVAILABLE,
            "verification_level": VerificationLevel.BASIC,
            "service_categories": [str(self.category.id)],
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)

    def _close_execution_session(self, supplier_assignment):
        session = ExecutionService.create_session(supplier_assignment=supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        return ExecutionService.close_session(session_id=session.id)

    @staticmethod
    def _invoice_items():
        return [
            {"item_type": "SERVICE", "description": "Home care visit", "quantity": 2, "unit_price": "500000"},
            {"item_type": "TRAVEL", "description": "Travel fee", "quantity": 1, "unit_price": "50000"},
        ]
