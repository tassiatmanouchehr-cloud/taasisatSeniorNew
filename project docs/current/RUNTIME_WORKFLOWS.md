# RUNTIME WORKFLOWS

**Last verified HEAD:** phase1-verification-activation-rules (from main @ 278098b)
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
| 15 | Manual Document Verification (caregiver/organization) | IMPLEMENTED | `accounts/services/verification_review_service.py:VerificationReviewService` |
| 16 | Profile Verification Roll-up | IMPLEMENTED (Phase 1.2) | `accounts/services/verification_rollup_service.py:ProfileVerificationRollupService` |
| 17 | Document Resubmission (correction lifecycle) | IMPLEMENTED (Phase 1.2) | `accounts/services/document_service.py:DocumentService.resubmit()` |
| 18 | Activation Eligibility (read-only) | IMPLEMENTED (Phase 1.2) | `accounts/services/activation_eligibility_service.py:ActivationEligibilityService` |

---

## Manual Document Verification Workflow (Phase 1.1, extended Phase 1.2)

1. Caregiver/organization uploads a document via `DocumentService.upload_*_document()` — enters PENDING.
2. Platform reviewer (role `platform_owner`/`platform_admin`/`platform_support`, permission `accounts.document.review`) opens `/admin-portal/verification/documents/` (queue) and a document's detail page.
3. Reviewer approves, rejects (reason required), or requests correction (reason required) via `VerificationReviewService.approve()/reject()/request_correction()`.
4. Legal transitions: PENDING → {VERIFIED, REJECTED, CORRECTION_REQUIRED} only. Same-outcome repeat calls are idempotent no-ops; any other non-PENDING call raises a controlled `VerificationReviewError`. Row-locked (`select_for_update()`) so concurrent conflicting reviews leave exactly one winner.
5. Every review action is recorded in `AuditLog` (actor, before/after status, reason). The same transaction also syncs the owning profile's rolled-up `verification_status` (Phase 1.2, step 6 below).
6. Owner sees current status and (for REJECTED/CORRECTION_REQUIRED) the reviewer's reason on their own portal page — never on any public page.

## Correction and Resubmission Lifecycle (Phase 1.2)

1. Owner resubmits a REJECTED/CORRECTION_REQUIRED (or PENDING) document via `DocumentService.resubmit(document, actor=request.user, file=...)` — replaces `apps.provider_portal`/`apps.organization_portal`'s direct `replace_document()` call from Phase 1.1.
2. Refuses unless `actor` is the document's own owner user; refuses to touch an already-VERIFIED document (an owner can no longer silently discard a platform decision).
3. Resets status to PENDING (delegates to `replace_document()`'s existing file-swap mechanics), records an `accounts.document.resubmitted` `AuditLog` entry (the original review's reason remains permanently in its own, earlier `AuditLog` entry — never overwritten), and re-syncs the profile roll-up.
4. Row-locked — concurrent resubmissions of the same document serialize.

## Profile Verification Roll-up (Phase 1.2)

`ProfileVerificationRollupService.evaluate_caregiver()/evaluate_organization()` derives the existing `CaregiverProfile`/`OrganizationProfile.verification_status` (UNVERIFIED/PENDING/VERIFIED/REJECTED — no new value added) from `RequiredDocumentPolicy`'s required-document set for that profile type: any required document REJECTED → profile REJECTED; any required document CORRECTION_REQUIRED (none rejected) → profile PENDING with `needs_correction=True`; any required document missing/PENDING/effectively-expired → profile PENDING; all required documents VERIFIED and unexpired → profile VERIFIED. Optional document status never affects this. `sync_*()` persists the result (row-locked, idempotent no-op if unchanged) and is called automatically from `VerificationReviewService` and `DocumentService.resubmit()` — never from a view, admin action, or signal.

## Required-Document Policy (Phase 1.2)

`RequiredDocumentPolicy` (mandatory vs optional document types per profile type, tenant-overridable via the existing `ConfigResolver`): caregiver required = IDENTITY + BACKGROUND_CHECK (optional: QUALIFICATION, TRAINING_CERTIFICATE, LICENSE); organization required = REGISTRATION + OPERATING_LICENSE (optional: INSURANCE, PROFESSIONAL_PERMIT). No per-service variation (no repository infrastructure ties `ServiceCategory`/`ServiceType` to document requirements). Customer document verification and profile-level roll-up were explicitly deferred by Phase 1.1 — the roll-up gap is now closed by this phase; customer document verification remains deferred (no domain-model support exists — see `traceability/IMPLEMENTATION_JOURNAL.md` and `quality/COMPLETION_BACKLOG.md` BG-016).

## Activation Eligibility (Phase 1.2, read-only)

`ActivationEligibilityService.evaluate(profile)` returns a structured `eligible: bool` + `reasons: tuple[str, ...]` + the underlying `VerificationRollupResult`, for caregiver or organization. Eligible requires: profile `status == ACTIVE`, underlying `UserAccount.is_active`, base-profile completion at 100% (`calculate_caregiver_profile_completion()`/new `calculate_organization_profile_completion()`), and rolled-up `verification_status == VERIFIED`. Pure read, no side effects — nothing currently calls this to actually activate or publish a profile; wiring it into a real activation action is future work (see `03_NEXT_TASK.md`).

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
