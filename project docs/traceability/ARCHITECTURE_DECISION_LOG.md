# ARCHITECTURE DECISION LOG

**Repository:** taasisatSenior
**Scope:** Offer Marketplace epic decisions only
**Policy:** Each decision is recorded once, with status tracking

---

## ADM-001: OrderOffer.SELECTED Represents the Temporary Hold

```
Decision ID: ADM-001
Context: The marketplace golden flow requires a 30-minute hold after customer selection.
         First draft proposed a separate reservation table.
Decision: OrderOffer.SELECTED status IS the temporary hold. No separate reservation model.
Alternatives considered:
  A. Separate Reservation model (rejected — unnecessary complexity, OrderOffer already carries all needed data)
  B. SupplierAssignment.PROPOSED as hold (rejected — wrong semantic, allows provider confirm/decline during hold)
  C. New field on Order model (rejected — Order should not carry offer lifecycle state)
Reason: OrderOffer already has status, hold_expires_at, selected_at fields. Adding a separate table duplicates data and creates synchronization risk.
Affected code: None yet (contract phase)
Risks: None — simplifies the design
Status: Accepted
```

## ADM-002: SupplierAssignment Created Only After Payment Success

```
Decision ID: ADM-002
Context: The marketplace golden flow requires assignment timing decision.
         Option A: at offer selection before payment; Option B: only after successful payment.
Decision: Option B — SupplierAssignment is created only after successful payment.
Alternatives considered:
  A. Create at selection (rejected — premature side effects: status change, capacity reduction, notification, provider actions)
  B. Create after payment (accepted — clean financial flow, no premature mutations)
Reason: Tracing every side effect of AssignmentService.assign() shows 10+ downstream effects that would fire prematurely if called at selection time.
Affected code: OrderOfferService.select_offer() does NOT call AssignmentService.assign(). Payment success wiring calls confirm_payment() which calls assign().
Risks: Order stays NEW during hold — caregivers may see it as available (addressed by ADM-003)
Status: Accepted
```

## ADM-003: Order Hidden from Marketplace During Active Hold

```
Decision ID: ADM-003
Context: Order stays NEW during hold (ADM-002), but should not appear as freely available.
Decision: Marketplace discovery query adds guard: no OrderOffer with status=SELECTED exists for the order.
Alternatives considered:
  A. Change Order status to HOLDING (rejected — adds complexity, breaks "order must be NEW" invariant)
  B. Hide via discovery query guard (accepted — minimal change, preserves Order status semantics)
  C. Add a boolean flag on Order (rejected — denormalized, synchronization risk)
Reason: The guard is a single WHERE clause addition to the discovery query. Order status remains NEW, which is semantically correct (the order IS still open, just temporarily reserved).
Affected code: OrderDiscoveryService.query(), offer submission guard
Risks: None — the guard is idempotent and atomic
Status: Accepted
```

## ADM-004: Selection Policy — One Active Hold Per Order

```
Decision ID: ADM-004
Context: Customer may attempt to select multiple offers. Need unambiguous policy.
Decision: Selecting a different offer while a hold is active is REJECTED. Customer must wait for expiry or cancel.
Alternatives considered:
  A. Replace old selection with new (rejected — complex state management, old offer's payment flow unclear)
  B. Reject new selection (accepted — simple, predictable, matches real-world UX)
  C. Queue new selection (rejected — over-engineered for initial implementation)
Reason: Simplicity and predictability. Customer sees clear error message. No complex rollback needed.
Affected code: OrderOfferService.select_offer() checks for existing SELECTED offer
Risks: Customer may be frustrated if hold is long — mitigated by 30-minute limit
Status: Accepted
```

## ADM-005: Payment Failure Does NOT Expire the Hold

```
Decision ID: ADM-005
Context: Payment may fail during the 30-minute hold. Need to define behavior.
Decision: Payment failure leaves the hold active. Customer may retry.
Alternatives considered:
  A. Expire on failure (rejected — punitive, customer may retry immediately)
  B. Leave hold active (accepted — customer-centric, allows retry)
  C. Reduce hold time on failure (rejected — complex, no clear benefit)
Reason: Real-world payment failures are often transient (network timeout, insufficient funds). Customer should be able to retry without losing the hold.
Affected code: PaymentCallbackService — FAILED status does not trigger any offer state change
Risks: Hold time continues counting down during retries — customer must succeed within 30 minutes total
Status: Accepted
```

## ADM-006: Ownership Enforced Inside Service Methods

```
Decision ID: ADM-006
Context: Authorization was previously portal-view-only. Need defense in depth.
Decision: All service methods enforce ownership and tenant checks internally.
Alternatives considered:
  A. View-only authorization (rejected — API callers bypass views)
  B. Service-level enforcement (accepted — defense in depth)
  C. Middleware-level enforcement (rejected — too coarse, doesn't know business context)
Reason: API endpoints and future integrations may bypass portal views. Service-level checks ensure no unauthorized access regardless of entry point.
Affected code: All OrderOfferService methods
Risks: Slight performance overhead from additional queries — acceptable for correctness
Status: Accepted
```

## ADM-007: PostgreSQL Required for Transaction and Constraint Tests

```
Decision ID: ADM-007
Context: SQLite cannot test UniqueConstraint conditions, select_for_update, or concurrent transactions.
Decision: All service, transaction, constraint, and concurrency tests must use PostgreSQL.
Alternatives considered:
  A. SQLite for unit tests (rejected — cannot test constraints, locking, or concurrency)
  B. PostgreSQL for all tests (accepted — matches production, tests real behavior)
  C. Mock database (rejected — does not test real ORM behavior)
Reason: The repository's existing test suite uses PostgreSQL. UniqueConstraint conditions and select_for_update are PostgreSQL-specific features that SQLite does not support.
Affected code: Test configuration (DATABASE_ENGINE=django.db.backends.postgresql)
Risks: Tests require running PostgreSQL — documented requirement
Status: Accepted
```

## ADM-008: Existing Operator-Assignment Flow Must Remain Functional

```
Decision ID: ADM-008
Context: The offer flow is an alternative to operator-assignment, not a replacement.
Decision: The existing matching→operator-assign flow continues to work unchanged.
Alternatives considered:
  A. Replace operator-assignment with offer flow (rejected — breaking change)
  B. Keep both flows (accepted — additive change)
  C. Deprecate operator-assignment (rejected — out of scope)
Reason: Existing customers and operators use the current flow. The offer flow is a new capability, not a replacement.
Affected code: None — existing AssignmentService.assign() is called unchanged at payment time
Risks: Two parallel flows may confuse users — mitigated by clear UI separation
Status: Accepted
```

## ADM-009: Real PSP, SMS, PR-C, and Production Integration Outside Scope

```
Decision ID: ADM-009
Context: The Offer Marketplace epic should not attempt to add real external integrations.
Decision: Real PSP, SMS, PR-C (release instruction consumption), and production deployment remain outside this epic.
Alternatives considered:
  A. Include real PSP (rejected — massive scope expansion, separate workstream)
  B. Include PR-C (rejected — separate epic with its own dependencies)
  C. Keep epic focused (accepted — deliverable increment)
Reason: The Offer Marketplace is a UI and workflow layer. Real integrations are separate workstreams with their own timelines and risks.
Affected code: None — FakePaymentProviderAdapter continues to be used for testing
Risks: E2E tests use fake providers — documented limitation
Status: Accepted
```

## ADM-010: Money Representation — DecimalField(14,2)

```
Decision ID: ADM-010
Context: Repository has two money representations: DecimalField(14,2) and integer IRR.
Decision: OrderOffer uses DecimalField(max_digits=14, decimal_places=2), matching Quote, FinancialDocument, PaymentIntent, Wallet.
Alternatives considered:
  A. Integer IRR (rejected — used only in EscrowRecord PR-B fields and AllocationCalculator, not customer-facing)
  B. DecimalField(14,2) (accepted — canonical representation across 49 usages in codebase)
  C. FloatField (rejected — precision loss, never used for money in this codebase)
Reason: DecimalField(14,2) is the repository's canonical money representation, used consistently across all customer-facing financial models.
Affected code: OrderOffer.price_amount field definition
Risks: None — matches existing patterns
Status: Accepted
```

## ADM-011: Existing Deadline Engine Reuse

```
Decision ID: ADM-011
Context: Need 30-minute hold mechanism. Repository has PaymentDeadline infrastructure.
Decision: Extend existing PaymentDeadline model to support OrderOffer hold target.
Alternatives considered:
  A. Extend PaymentDeadline (accepted — reuse existing scheduler, retry, audit infrastructure)
  B. Create separate deadline engine (rejected — duplicates infrastructure)
  C. Use Django-Celery-Beat directly (rejected — bypasses existing audit/retry logic)
  D. Use simple datetime check (rejected — no scheduler integration, no retry)
Reason: PaymentDeadline already has: scheduler integration, retry logic, idempotent expiry, audit logging, feature gates. Extending it avoids duplicating this infrastructure.
Affected code: PaymentDeadline model (add nullable order_offer FK), PaymentDeadlineService (add create_for_offer method)
Risks: Must not break existing commission deadline workflow — mitigated by nullable FK and separate creation path
Status: Accepted in principle — pending contract-level compatibility proof (see Remediation 2 in contract)
```

## ADM-012: PaymentIntent → OrderOffer Link (1:N)

```
Decision ID: ADM-012
Context: One OrderOffer may have multiple PaymentIntents (retries). The original contract proposed
         OrderOffer.payment_intent FK (1:1), which cannot safely represent multiple attempts.
Decision: Add nullable order_offer FK to PaymentIntent. Remove payment_intent FK from OrderOffer.
Alternatives considered:
  A. OrderOffer.payment_intent FK (rejected — 1:1 cannot represent retries)
  B. PaymentIntent.order_offer FK (accepted — 1:N, each retry is a new intent)
  C. Use metadata only (rejected — unvalidated JSON is not integrity-enforced)
Reason: Multiple retries are a real user scenario. The 1:N relationship on PaymentIntent is the
        least invasive safe design. confirm_payment() receives and validates the exact successful intent.
Affected code: PaymentIntent model (add nullable FK), OrderOffer model (remove payment_intent FK)
Risks: Migration adds nullable FK to PaymentIntent — safe, no data migration needed
Status: RESOLVED_IN_CONTRACT
```

## ADM-013: One Canonical OrderOffer per (order, supplier)

```
Decision ID: ADM-013
Context: Phase 1 initially implemented a conditional UniqueConstraint allowing multiple offers
         per (order, supplier) when older offers reached terminal status. Architecture review
         determined this creates ambiguous identity: a supplier could have ACCEPTED, EXPIRED,
         and WITHDRAWN offers on the same order simultaneously, making reporting, audit trails,
         and future service logic unreliable.
Decision: Exactly one canonical OrderOffer exists per (order, supplier). The unconditional
         UniqueConstraint enforces this at the database level. A second row must never be
         created. Future resubmission (after withdrawal, expiry, etc.) updates or reactivates
         the existing record.
Alternatives considered:
  A. Conditional uniqueness on active statuses only (rejected — ambiguous identity, unreliable audit)
  B. Unconditional uniqueness (accepted — stable identity, clean audit history, reliable reporting)
  C. Separate offer history table (rejected — over-engineered for Phase 1, can be added later)
Reason: Unconditional uniqueness provides: (1) stable identity for every supplier's relationship
        to an order, (2) complete audit history in one row, (3) reliable reporting and aggregation,
        (4) simpler service logic with no edge cases around status transitions.
Affected code: OrderOffer model Meta.constraints, migration 0008_orderoffer.py
Risks: Future "resubmit" logic must update the existing row, not create a new one. This is a
       design constraint that must be enforced in OrderOfferService.submit_offer().
Status: VERIFIED_IN_IMPLEMENTATION — unconditional constraint in place, 40 tests passing
```

## ADM-014: VerificationDocument.rejection_reason Becomes Owner-Visible

```
Decision ID: ADM-014
Context: Phase 1.1 (Manual Document Verification) implements the platform-admin review
         workflow apps.accounts.models.media's own module docstring named as future/
         out-of-scope for Epic 06 Sprint 2. That Sprint declared rejection_reason
         "Staff-authored, internal-only — never rendered on any provider/organization-facing
         or public page." The current task's explicit business requirement #6 is the direct
         opposite: "The document owner can see: current review status; rejection/correction
         reason; whether resubmission is required."
Decision: rejection_reason is now rendered on the owning caregiver's/organization's own
         portal page (document_upload.html, via document_status.html's action_message prop)
         whenever the document's status is REJECTED or CORRECTION_REQUIRED. It is still never
         rendered on any PUBLIC page (public_site caregiver/organization profiles are
         untouched by this task).
Alternatives considered:
  A. Keep rejection_reason internal-only; add a second, separate "owner-facing message" field
     (rejected — a genuine second field the reviewer would have to fill out twice, and the
     task's own governance says "do not create parallel status/data systems" without cause;
     no such duplication was needed once the internal-only constraint itself was reconsidered)
  B. Reverse the internal-only constraint, reuse the existing field for both purposes
     (accepted — the field's actual content, a reviewer's plain-language reason, was never
     unsafe to show its own subject; the Sprint 2 restriction predates this task's explicit
     opposite requirement)
Reason: A reviewer's reason for rejecting a document is written FOR the person who must act on
        it. Continuing to hide it would make "request correction" meaningless (the owner would
        not know what to correct) and directly contradicts this task's explicit spec.
Affected code: apps/accounts/models/media.py (VerificationDocument.rejection_reason docstring),
        ui/components/portal/document_status.html (action_message prop docstring),
        templates/provider_portal/document_upload.html, templates/organization_portal/document_upload.html
Risks: None — the field's content is authored by platform staff specifically to be actionable
        by the document owner; no PII/internal-system data was ever stored there by design
        (DisputeResolveForm-style internal notes live elsewhere, e.g. AuditLog.reason, and
        remain internal).
Status: RESOLVED_IN_IMPLEMENTATION — 41 tests passing (25 service + 16 view), including
        explicit owner-visibility and cross-tenant/self-review denial coverage
```
