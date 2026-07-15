# RUNTIME WORKFLOWS

**Last verified HEAD:** phase1-registration-manual-verification (from main @ 55b1cb0)
**Last verified date:** 2026-07-15

---

## Workflow Implementation Status

| # | Workflow | Status | Key Entry Point |
|---|----------|--------|-----------------|
| 1 | Authentication (OTP) | IMPLEMENTED (fake SMS) | `accounts/views.py:verify_view` |
| 2 | Customer Registration | IMPLEMENTED | `accounts/services/registration_service.py` |
| 3 | Order Creation | IMPLEMENTED | `orders/services/order_creation.py:create_operator_order()` |
| 4 | Matching | IMPLEMENTED | `matching/services/match_orchestrator.py:run()` |
| 5 | Assignment | IMPLEMENTED | `booking/services/assignment_service.py:assign()` |
| 6 | Execution | IMPLEMENTED | `execution/services/session_service.py:create_session()` |
| 7 | Payment | MOCKED PSP | `payments/services/payment_intent_service.py:create_intent()` |
| 8 | Escrow | IMPLEMENTED | `finance/services/escrow_service.py:hold_for_order()` |
| 9 | Deadline | IMPLEMENTED (gated) | `commission/services/deadline_service.py:create_for_order()` |
| 10 | Dispute | IMPLEMENTED | `commission/services/dispute_service.py:open()` |
| 11 | Notifications | MOCKED providers | `notifications/services/dispatch_service.py:dispatch_pending()` |
| 12 | Wallet | IMPLEMENTED | `wallet/services/wallet_service.py` + `wallet_transaction_service.py` |
| 13 | Reviews | IMPLEMENTED | `reviews/services/review_submission_service.py` |
| 14 | Offer Marketplace | MODEL ONLY (Phase 1) | No service layer yet |
| 15 | Manual Document Verification (caregiver/organization) | IMPLEMENTED (Phase 1.1) | `accounts/services/verification_review_service.py:VerificationReviewService` |

---

## Manual Document Verification Workflow (Phase 1.1)

1. Caregiver/organization uploads a document via `DocumentService.upload_*_document()` — enters PENDING.
2. Platform reviewer (role `platform_owner`/`platform_admin`/`platform_support`, permission `accounts.document.review`) opens `/admin-portal/verification/documents/` (queue) and a document's detail page.
3. Reviewer approves, rejects (reason required), or requests correction (reason required) via `VerificationReviewService.approve()/reject()/request_correction()`.
4. Legal transitions: PENDING → {VERIFIED, REJECTED, CORRECTION_REQUIRED} only. Same-outcome repeat calls are idempotent no-ops; any other non-PENDING call raises a controlled `VerificationReviewError`. Row-locked (`select_for_update()`) so concurrent conflicting reviews leave exactly one winner.
5. CORRECTION_REQUIRED → PENDING happens through the owner's existing `DocumentService.replace_document()` resubmission flow — no new code needed there.
6. Every review action is recorded in `AuditLog` (actor, before/after status, reason).
7. Owner sees current status and (for REJECTED/CORRECTION_REQUIRED) the reviewer's reason on their own portal page — never on any public page.
8. Customer document verification and profile-level roll-up (`CaregiverProfile.verification_status`/`OrganizationProfile.verification_status` auto-transition) are explicitly deferred — see `traceability/IMPLEMENTATION_JOURNAL.md`.

## Order Lifecycle (Status Machine)

```
NEW ──→ WAITING_SERVICE ──→ IN_PROGRESS ──→ COMPLETED
  ↑           │                    │
  │           ↓                    ↓
  │      CANCELLED            CANCELLED
  │
  └── (reopen on assignment expiry)

PUBLIC orders: PENDING_OPERATOR_REVIEW → NEW → ...
```

Status transitions are managed exclusively by `apps/orders/services/status_machine.py`. No other service mutates `Order.status` directly.

## Assignment → Financial Core Flow

When `AssignmentService.assign()` is called:

1. `Order.select_for_update()` — row lock
2. Tenant check
3. Permission check (`BOOKING_ASSIGNMENT_ASSIGN`)
4. Optional availability/capacity validation (gated)
5. `status_machine.assign_supplier()` → Order.status = WAITING_SERVICE
6. Create `SupplierAssignment` row
7. Mark `MatchCandidate` as SELECTED
8. Publish `Booking.Assignment.Created.v1` event
9. Publish `ORDER_ASSIGNED` domain event
10. `CommissionSnapshotService.create_snapshot_for_order()` — freeze commission policy
11. `PaymentDeadlineService.create_for_order()` — create deadline (optionally schedule expiry job)
12. `PreServicePaymentService.create_invoice_and_intent_for_order()` — gated, disabled by default

## Escrow Lifecycle

```
                     ┌─── hold_for_order() ───→ HELD
                     │
                     ├─── mark_releasable() ──→ moves remaining → releasable
                     │
                     ├─── block_for_dispute() → moves remaining → blocked
                     │
    HELD ────────────├─── unblock() ─────────→ moves blocked → remaining
                     │
                     ├─── apply_release() ────→ PARTIALLY_RELEASED → FULLY_RELEASED → CLOSED
                     │
                     └─── apply_refund() ─────→ PARTIALLY_REFUNDED → FULLY_REFUNDED → CLOSED
```

Conservation equation: `original_amount = held + remaining + releasable + blocked + released + refunded`

## Dispute Flow

1. Customer calls `DisputeService.open()` with disputed_amount and lines
2. Validates: feature gate, authorization (must be order customer), escrow state, amount bounds
3. Creates `Dispute` + `DisputeLine` rows
4. Calls `EscrowService.block_for_dispute()` — moves disputed amount from remaining to blocked
5. Transitions `ObjectionPeriod` to DISPUTED (if exists)

Resolution:
1. Admin calls `DisputeResolutionService.resolve()` with allocation (customer_refund + platform + company + caregiver)
2. Validates allocation sums to disputed amount
3. Creates `DisputeResolution` row
4. Calls `EscrowService.unblock()` — returns blocked to remaining
5. Creates `RefundInstruction` → `EscrowService.apply_refund()`
6. Creates `ReleaseInstruction` → `EscrowService.apply_release()`

## Deadline Expiry Flow

1. `PaymentDeadlineService.expire_due()` (scheduled job handler)
2. Row lock on deadline, idempotent check
3. Safety gate re-check: `deadline_activation_enabled` (DISABLED by default)
4. Transitions deadline to EXPIRED
5. Calls `AssignmentService.expire()`:
   - `status_machine.remove_supplier()` → Order goes back to NEW
   - Marks SupplierAssignment as EXPIRED
   - Publishes `Booking.Assignment.Expired.v1`

**Key insight**: The full cascade is implemented but gated. PaymentDeadline rows are created (data foundation) but expiry jobs are not scheduled unless gate is enabled.
