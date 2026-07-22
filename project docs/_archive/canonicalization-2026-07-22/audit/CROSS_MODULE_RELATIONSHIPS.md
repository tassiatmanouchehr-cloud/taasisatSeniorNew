# CROSS-MODULE RELATIONSHIPS

---

## Hub Entity: orders.Order

Order is the central hub referenced by:

| Module | Reference Type | FK Field |
|--------|---------------|----------|
| matching | MatchRound.order | CASCADE |
| booking | SupplierAssignment.order | CASCADE |
| execution | ExecutionSession.order | CASCADE |
| commission | PaymentDeadline.order | PROTECT |
| commission | CommissionSnapshot.order | PROTECT |
| commission | ObjectionPeriod.order | PROTECT |
| commission | Dispute.order | PROTECT |
| commission | ReleaseInstruction.order | PROTECT |
| commission | RefundInstruction.order | PROTECT |
| finance | FinancialDocument.order | SET_NULL |
| finance | EscrowRecord.order | SET_NULL |
| pricing | Quote.order | SET_NULL |
| reviews | Review.order | SET_NULL |
| orders | OrderOffer.order | CASCADE |
| orders | OrderShareLink.order | CASCADE |
| orders | OrderStatusHistory.order | CASCADE |
| orders | OrderOrganizationEligibility.order | CASCADE |

---

## Hub Entity: kernel.ServiceSupplier

Referenced by:

| Module | Model |
|--------|-------|
| availability | ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule |
| booking | SupplierAssignment |
| matching | MatchCandidate |
| orders | Order.assigned_supplier, OrderOffer.supplier |
| pricing | PricingRule, Quote, PromotionCondition |
| reviews | Review, ReputationSnapshot |
| commission | CommissionSnapshot |

---

## Hub Entity: finance.FinancialParty

Referenced by:

| Module | Model |
|--------|-------|
| finance | WalletAccount, WalletTransaction, PaymentTransaction, LedgerEntry, EscrowRecord, SettlementItem, FinancialDocument, FinancialObligation |
| commission | CommissionContract, CommissionSnapshot, Dispute |
| wallet | Wallet |
| payments | PaymentIntent |

---

## Key Cross-App Service Calls

| Caller | Callee | Method |
|--------|--------|--------|
| booking.AssignmentService.assign() | orders.status_machine.assign_supplier() | Order status mutation |
| booking.AssignmentService.assign() | commission.CommissionSnapshotService.create_snapshot_for_order() | Financial snapshot |
| booking.AssignmentService.assign() | commission.PaymentDeadlineService.create_for_order() | Deadline creation |
| booking.AssignmentService.assign() | commission.PreServicePaymentService.create_invoice_and_intent_for_order() | Preservice payment (gated) |
| execution.ExecutionService.close_session() | commission.ObjectionPeriodService._start_objection_period() | Objection period (gated) |
| commission.ObjectionPeriodService | finance.EscrowService.mark_releasable() | Escrow state |
| commission.DisputeService.open() | finance.EscrowService.block_for_dispute() | Escrow state |
| commission.DisputeResolutionService.resolve() | finance.EscrowService.unblock() + apply_release() + apply_refund() | Escrow state |
| payments.PaymentCallbackService | commission.SettlementOrchestrationService.settle_payment_intent() | Settlement |
| commission.PaymentDeadlineService.expire_due() | booking.AssignmentService.expire() | Assignment expiry |
