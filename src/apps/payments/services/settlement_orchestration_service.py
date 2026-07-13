"""
SettlementOrchestrationService — Sprint 1 (Epic 03, Financial Settlement &
Money Flow).

Connects existing, independently-tested financial services into the money
flow approved by the Financial Settlement Architecture Specification:

    PaymentIntent (SUCCEEDED)
        -> resolve FinancialDocument (existing document only — never fabricated)
        -> resolve/create FinancialObligation
        -> PaymentService.record_payment()
        -> SettlementAdjustmentPipeline.run() (Sprint 1: identity, net == gross)
        -> LedgerService.post_entries() (balanced platform/provider group)
        -> WalletTransactionService.credit() (canonical apps.wallet only)
        -> domain events (Finance.Settlement.Completed.v1, PaymentSettled,
           ProviderEarningsCredited)

This module does not create FinancialDocument rows and does not derive
invoice line items from a Quote/Order — Sprint 1 explicitly reuses the
existing document/obligation services and *resolves* an already-created
document. If no document exists yet for the order, settlement fails with a
clear SettlementError (a documented Sprint 1 limitation, not a silent
workaround).

Escrow (Financial Core PR-B): the legacy financial.escrow.enabled key
(apps.finance.services.configuration.FinanceConfiguration
.get_escrow_enabled()) is untouched and still governs nothing here — it
predates PR-B, defaults True, and was always a no-op warn-and-bypass (see
below); leaving it as dead/inert legacy config avoids silently changing
behavior for any tenant relying on its (never-enforced) default. The REAL
Escrow production path is a separate, PR-B-specific gate:
CommissionConfiguration.get_escrow_production_enabled(), default DISABLED
for every tenant, combined with the intent being tagged
metadata["financial_core_flow"] == "preservice" (only PreServicePaymentService
ever creates such an intent). When both are true, settle_payment_intent()
routes to _settle_preservice_to_escrow() instead of Direct Settlement: no
beneficiary wallet is credited, no ledger direct-settlement entries are
posted — a PaymentTransaction is still recorded (for reconciliation; its
receiver_party is the platform party, since the money is held, not yet
allocated to any final beneficiary), and
apps.commission.services.escrow_integration_service.EscrowIntegrationService
takes it from there (completing the PaymentDeadline, creating the Escrow
hold). Every other PaymentIntent — including every legacy, non-preservice
intent, on every tenant regardless of this new gate's value — continues
through the exact, unmodified Direct Settlement path below.

Idempotency: PaymentCallbackService.process_callback() already dedupes on
provider_event_id before this service is ever invoked. As defense in
depth, this service independently short-circuits if a SUCCEEDED
PaymentTransaction already exists with provider_reference == str(intent.id).
"""

import logging

from django.db import transaction

from apps.finance.models import (
    FinancialDocumentStatus,
    LedgerEntryType,
    ObligationStatus,
    PaymentMethod,
    PaymentTransaction,
)
from apps.finance.models import PaymentStatus as FinancePaymentStatus
from apps.finance.services import (
    FinanceConfiguration,
    FinancialDocumentService,
    FinancialPartyService,
    LedgerService,
    ObligationService,
    PaymentService,
)
from apps.kernel.events.base import PAYMENT_SETTLED, PROVIDER_EARNINGS_CREDITED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.services.event_publisher import EventPublisher
from apps.orders.models import Order
from apps.wallet.services import WalletService, WalletTransactionService

from ..models import PaymentIntent
from ..models import PaymentStatus as PaymentsPaymentStatus
from .errors import PaymentError
from .settlement_adjustments import SettlementAdjustmentPipeline

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"

ACCOUNT_CASH_COLLECTED = "platform.cash.collected"
ACCOUNT_RECEIVABLE_SETTLED = "provider.receivable.settled"
ACCOUNT_COMMISSION_REVENUE = "platform.commission.revenue"  # reserved; unused while commission == 0

_OPEN_OBLIGATION_STATUSES = (
    ObligationStatus.CREATED,
    ObligationStatus.DUE,
    ObligationStatus.PARTIALLY_RESOLVED,
)
_DOCUMENT_EXCLUDED_STATUSES = (FinancialDocumentStatus.CANCELLED, FinancialDocumentStatus.VOIDED)


class SettlementError(PaymentError):
    """Raised when a PaymentIntent cannot be settled (missing document, unresolved reference, ...)."""


class SettlementOrchestrationService:
    """Orchestrates the direct-settlement money flow for a SUCCEEDED PaymentIntent."""

    @classmethod
    @transaction.atomic
    def settle_payment_intent(cls, *, payment_intent_id) -> PaymentTransaction:
        # select_for_update() is the concurrency guarantee: it serializes any
        # two overlapping calls to settle_payment_intent() for the same
        # intent (e.g. the synchronous callback path racing a future retry
        # job) on this row lock. A second caller blocks here until the first
        # caller's transaction commits or rolls back, then re-reads a
        # consistent existing_payment below — a plain read-then-write check
        # alone cannot make that guarantee (see uq_payment_transaction_tenant_
        # provider_reference / uq_ledger_entry_payment_txn_account_code for
        # the database-level backstop if this lock is ever bypassed).
        intent = PaymentIntent.objects.select_for_update().get(id=payment_intent_id)
        tenant_id = intent.tenant_id

        existing_payment = PaymentTransaction.objects.filter(
            tenant_id=tenant_id,
            provider_reference=cls._provider_reference(intent),
            status=FinancePaymentStatus.SUCCEEDED,
        ).first()
        if existing_payment is not None:
            return existing_payment

        if intent.status != PaymentsPaymentStatus.SUCCEEDED:
            raise SettlementError(
                f"PaymentIntent {intent.id} is in '{intent.status}' status; only SUCCEEDED intents can be settled.",
            )

        if intent.reference_type != "Order" or not intent.reference_id:
            raise SettlementError(
                f"PaymentIntent {intent.id} does not reference an Order "
                f"(reference_type={intent.reference_type!r}); cannot settle.",
            )

        try:
            order = Order.objects.select_related("customer_profile", "assigned_supplier", "tenant").get(
                id=intent.reference_id,
                tenant_id=tenant_id,
            )
        except Order.DoesNotExist as exc:
            raise SettlementError(
                f"PaymentIntent {intent.id} references Order {intent.reference_id}, which does not exist.",
            ) from exc

        if not order.assigned_supplier_id:
            raise SettlementError(
                f"Order {order.id} has no assigned_supplier; cannot resolve a settlement beneficiary.",
            )

        if cls._is_preservice_escrow_intent(intent):
            return cls._settle_preservice_to_escrow(intent=intent, order=order, tenant_id=tenant_id)

        document = cls._resolve_document(order=order)
        obligation = cls._resolve_obligation(document=document)

        if FinanceConfiguration.get_escrow_enabled(tenant_id=tenant_id):
            logger.warning(
                "Escrow is configured (financial.escrow.enabled=True) for tenant %s but Sprint 1 only "
                "implements Direct Settlement. Falling back to Direct Settlement for PaymentIntent %s. This "
                "legacy key is distinct from the real Financial Core PR-B Escrow production path (see module "
                "docstring) — it has never been enforced and is left inert here to avoid a silent behavior "
                "change for tenants that may already have it set to its own default (True).",
                tenant_id,
                intent.id,
            )

        beneficiary_party = FinancialPartyService.resolve_party_for_supplier(order.assigned_supplier)

        payment = PaymentService.record_payment(
            payer_party_id=intent.payer_party_id,
            receiver_party_id=beneficiary_party.id,
            amount=intent.amount,
            payment_method=PaymentMethod.ONLINE,
            currency=intent.currency,
            source_document_id=document.id,
            obligation_id=obligation.id,
            status=FinancePaymentStatus.SUCCEEDED,
            provider_reference=cls._provider_reference(intent),
        )

        adjustment = SettlementAdjustmentPipeline.run(gross_amount=intent.amount)

        cls._post_ledger_entries(
            tenant_id=tenant_id,
            order=order,
            payment=payment,
            adjustment=adjustment,
            beneficiary_party=beneficiary_party,
        )

        wallet = WalletService.get_or_create_wallet(party=beneficiary_party, currency=intent.currency)
        WalletTransactionService.credit(
            wallet_id=wallet.id,
            amount=adjustment.net_amount,
            reason="Settlement of PaymentIntent",
            metadata={"payment_intent_id": str(intent.id), "payment_transaction_id": str(payment.id)},
            idempotency_key=f"settlement:{intent.id}",
        )

        cls._publish_settlement_events(
            tenant_id=tenant_id,
            intent=intent,
            order=order,
            payment=payment,
            beneficiary_party=beneficiary_party,
            adjustment=adjustment,
        )

        return payment

    # --- Financial Core PR-B: real production Escrow path ------------------

    @staticmethod
    def _is_preservice_escrow_intent(intent: PaymentIntent) -> bool:
        from apps.commission.services.configuration import CommissionConfiguration

        if intent.metadata.get("financial_core_flow") != "preservice":
            return False
        return CommissionConfiguration.get_escrow_production_enabled(tenant_id=intent.tenant_id)

    @classmethod
    def _settle_preservice_to_escrow(cls, *, intent, order, tenant_id) -> PaymentTransaction:
        """Records a PaymentTransaction (receiver_party is the platform
        party — the money is held, not yet allocated to any final
        beneficiary) and hands off to EscrowIntegrationService for the
        PaymentDeadline-completion + Escrow-hold specifics. No wallet is
        credited and no ledger direct-settlement entries are posted here —
        that is exactly the point of this path."""
        from apps.commission.services.escrow_integration_service import EscrowIntegrationService

        platform_party = FinancialPartyService.resolve_platform_party(order.tenant)

        payment = PaymentService.record_payment(
            payer_party_id=intent.payer_party_id,
            receiver_party_id=platform_party.id,
            amount=intent.amount,
            payment_method=PaymentMethod.ONLINE,
            currency=intent.currency,
            status=FinancePaymentStatus.SUCCEEDED,
            provider_reference=cls._provider_reference(intent),
            metadata={"financial_core_flow": "preservice", "held_in_escrow": True},
        )

        # Deliberately does NOT call _publish_settlement_events(): that
        # method publishes PaymentSettled/ProviderEarningsCredited, which
        # would be factually wrong here — no provider earnings exist yet,
        # the money is held pending objection/dispute review.
        # EscrowService.hold_for_order() (called inside
        # handle_preservice_payment_succeeded below) publishes its own
        # Finance.Escrow.Held.v1 event and FINANCIAL audit record instead.
        EscrowIntegrationService.handle_preservice_payment_succeeded(intent=intent, payment_transaction=payment)

        return payment

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _provider_reference(intent: PaymentIntent) -> str:
        return str(intent.id)

    @classmethod
    def _resolve_document(cls, *, order):
        document = (
            order.financial_documents.exclude(status__in=_DOCUMENT_EXCLUDED_STATUSES).order_by("-created_at").first()
        )
        if document is None:
            raise SettlementError(
                f"Order {order.id} has no FinancialDocument to settle against. A FinancialDocument must "
                "be created (e.g. via FinancialDocumentService.create_invoice_from_execution()) before "
                "payment can be settled.",
            )
        if document.status == FinancialDocumentStatus.DRAFT:
            document = FinancialDocumentService.issue_document(document_id=document.id, changed_by=None)
        return document

    @classmethod
    def _resolve_obligation(cls, *, document):
        obligation = document.obligations.filter(status__in=_OPEN_OBLIGATION_STATUSES).order_by("-created_at").first()
        if obligation is None:
            obligation = ObligationService.create_obligations_for_document(document_id=document.id)
        return obligation

    @classmethod
    def _post_ledger_entries(cls, *, tenant_id, order, payment, adjustment, beneficiary_party):
        platform_party = FinancialPartyService.resolve_platform_party(order.tenant)

        entries = [
            {
                "party_id": platform_party.id,
                "entry_type": LedgerEntryType.DEBIT,
                "account_code": ACCOUNT_CASH_COLLECTED,
                "amount": adjustment.gross_amount,
                "currency": payment.currency,
                "payment_transaction_id": payment.id,
                "description": "Gross payment collected from customer.",
            },
            {
                "party_id": beneficiary_party.id,
                "entry_type": LedgerEntryType.CREDIT,
                "account_code": ACCOUNT_RECEIVABLE_SETTLED,
                "amount": adjustment.net_amount,
                "currency": payment.currency,
                "payment_transaction_id": payment.id,
                "description": "Net settlement credited to provider.",
            },
        ]

        # Extension point: once a future sprint's adjustment pipeline
        # returns a non-zero commission, a third balancing line is posted
        # here. Sprint 1's pipeline always returns zero, so this branch
        # never executes today.
        if adjustment.commission_amount > 0:
            entries.append(
                {
                    "party_id": platform_party.id,
                    "entry_type": LedgerEntryType.CREDIT,
                    "account_code": ACCOUNT_COMMISSION_REVENUE,
                    "amount": adjustment.commission_amount,
                    "currency": payment.currency,
                    "payment_transaction_id": payment.id,
                    "description": "Marketplace commission revenue.",
                }
            )

        return LedgerService.post_entries(tenant_id=tenant_id, entries=entries, actor=None)

    @classmethod
    def _publish_settlement_events(cls, *, tenant_id, intent, order, payment, beneficiary_party, adjustment):
        EventPublisher.publish(
            tenant_id=tenant_id,
            event_type="Finance.Settlement.Completed.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=payment.id,
            source_entity_type="PaymentTransaction",
            payload={
                "payment_intent_id": str(intent.id),
                "order_id": str(order.id),
                "gross_amount": str(adjustment.gross_amount),
                "net_amount": str(adjustment.net_amount),
                "commission_amount": str(adjustment.commission_amount),
                "beneficiary_party_id": str(beneficiary_party.id),
            },
        )

        payment_settled = DomainEvent(
            event_type=PAYMENT_SETTLED,
            tenant_id=tenant_id,
            aggregate_type="PaymentTransaction",
            aggregate_id=payment.id,
            payload={
                "payment_intent_id": str(intent.id),
                "order_id": str(order.id),
                "amount": str(payment.amount),
                "currency": payment.currency,
            },
        )
        provider_earnings_credited = DomainEvent(
            event_type=PROVIDER_EARNINGS_CREDITED,
            tenant_id=tenant_id,
            aggregate_type="FinancialParty",
            aggregate_id=beneficiary_party.id,
            payload={
                "payment_intent_id": str(intent.id),
                "order_id": str(order.id),
                "net_amount": str(adjustment.net_amount),
                "currency": payment.currency,
            },
        )
        transaction.on_commit(lambda: publish_domain_event(payment_settled))
        transaction.on_commit(lambda: publish_domain_event(provider_earnings_credited))
