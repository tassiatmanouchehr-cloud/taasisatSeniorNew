# CONTRACT DIFF SUMMARY

**Repository:** taasisatSenior
**Contract:** OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md
**Session:** Final Remediation

---

## ADDED

### Section 1.5 — Marketplace Visibility Guard
- **Content:** Discovery query guard: `NOT EXISTS (SELECT 1 FROM orders_orderoffer WHERE order_id = orders_order.id AND status = 'selected')`
- **Reason:** Order must be hidden from caregiver marketplace during active hold

### Section 9.4 — PaymentDeadline Reuse (Compatibility Proof)
- **Content:** 9-point compatibility matrix proving PaymentDeadline can support offer holds. Required changes: nullable order_offer FK + routing in expire_due().
- **Reason:** Reuse existing deadline infrastructure instead of creating duplicate engine

### REJECTED Semantics Definition (in Section 3.1)
- **Content:** "REJECTED is NOT a direct transition from SELECTED. REJECTED is set in bulk by confirm_payment() on all other SUBMITTED offers for the same order."
- **Reason:** Clarify that REJECTED is a post-payment bulk operation, not a state transition from SELECTED

### CANCELLED Semantics Definition (in Section 3.1)
- **Content:** "CANCELLED applies to all active offers (SUBMITTED and SELECTED) when the order is cancelled. This is a bulk operation triggered by order cancellation."
- **Reason:** Clarify CANCELLED as a bulk operation on order cancellation

### Step 5 in confirm_payment() (Section 5.3)
- **Content:** "Bulk update: all other SUBMITTED offers for same order → REJECTED"
- **Reason:** Wire the REJECTED bulk operation into the payment confirmation flow

### Step 6 in confirm_payment() (Section 5.3)
- **Content:** "Mark PaymentDeadline as COMPLETED (via PaymentDeadlineService.mark_completed)"
- **Reason:** Wire deadline completion into payment confirmation

### deadline.py to Modified Files (Section 13.2)
- **Content:** `apps/commission/models/deadline.py` — Add nullable order_offer FK
- **Reason:** PaymentDeadline reuse requires schema change

### deadline_service.py to Modified Files (Section 13.2)
- **Content:** `apps/commission/services/deadline_service.py` — Add create_for_offer(), routing in expire_due()
- **Reason:** PaymentDeadline reuse requires service changes

---

## MODIFIED

### Section 1.5 — Order Status During Hold
- **Previous meaning:** "Other caregivers can still see the order (it's still available)"
- **New meaning:** Order hidden from marketplace during hold via NOT EXISTS guard. Includes behavior table by phase.
- **Reason:** Remediation 1 — marketplace visibility during active hold

### Section 3.1 — OrderOffer State Machine Diagram
- **Previous meaning:** ASCII art included `select_other() ─── REJECTED` transition from SELECTED
- **New meaning:** ASCII art shows REJECTED as a bulk post-payment operation, not a state transition
- **Reason:** Remediation 3 — REJECTED semantics

### Section 3.1 — Transition Rules Table
- **Previous meaning:** Had `SELECTED | REJECTED | select_other() | Customer selected a different offer`
- **New meaning:** Removed SELECTED → REJECTED row. Added SUBMITTED → CANCELLED and SELECTED → CANCELLED rows. Added REJECTED and CANCELLED semantics notes.
- **Reason:** Remediation 3 — REJECTED semantics

### Section 5.3 — confirm_payment() Transaction Boundary
- **Previous meaning:** 6 steps (lock, verify, verify, update, assign, publish)
- **New meaning:** 8 steps (lock, verify, verify, update, bulk REJECTED, mark deadline, assign, publish)
- **Reason:** Wire REJECTED bulk operation and deadline completion

### Section 9.4 — Hold Expiry Wiring
- **Previous meaning:** "Existing PaymentDeadlineService.expire_due() → AssignmentService.expire() cascade is NOT used. New job handler: orders.offer_hold.expire"
- **New meaning:** PaymentDeadline reuse with compatibility proof. Nullable order_offer FK + routing in expire_due().
- **Reason:** Remediation 2 — reuse existing deadline engine

### Section 13.2 — Modified Files
- **Previous meaning:** 9 files listed
- **New meaning:** 11 files listed (added deadline.py and deadline_service.py)
- **Reason:** PaymentDeadline reuse requires these files to change

### Section 13.3 — Files NOT Modified
- **Previous meaning:** 5 files listed (included deadline_service.py)
- **New meaning:** 4 files listed (removed deadline_service.py)
- **Reason:** deadline_service.py is now a modified file

---

## REMOVED

### SELECTED → REJECTED Transition (Section 3.1)
- **Removed statement:** `SELECTED | REJECTED | select_other() | Customer selected a different offer on the same order`
- **Reason:** Contradicts policy that second selection is rejected at entry point, not as a state transition

### select_other() from State Machine Diagram (Section 3.1)
- **Removed content:** `select_other() ─── REJECTED` line in ASCII art
- **Reason:** No such transition exists. REJECTED is a bulk post-payment operation.

### Separate Job Handler for Offer Hold Expiry (Section 9.4)
- **Removed content:** `apps/orders/jobs.py` with `_expire_offer_hold()` function
- **Reason:** Replaced by PaymentDeadline reuse

### orders.offer_hold.expire Job Type
- **Removed content:** `JobService.enqueue(job_type="orders.offer_hold.expire", ...)`
- **Reason:** Replaced by PaymentDeadline scheduler integration

---

## RISK-004 RESOLUTION ADDITIONS (Payment Retry Linkage)

### ADDED — Section 6A (PaymentIntent → OrderOffer Link)

- **Content:** New section defining 1:N cardinality, PaymentIntent.order_offer FK, confirm_payment signature with payment_intent_id, 12-step validation, idempotency rules, race handling, 10 required tests
- **Reason:** RISK-004 resolution — one OrderOffer may have multiple PaymentIntents

### MODIFIED — Section 2 (OrderOffer Model)

- **Previous:** `payment_intent = models.ForeignKey("payments.PaymentIntent", ...)`
- **New:** Comment noting FK is on PaymentIntent.order_offer, not on OrderOffer
- **Reason:** FK direction reversed for 1:N cardinality

### MODIFIED — Section 5.3 (confirm_payment Transaction Boundary)

- **Previous:** 8 steps (lock offer, verify, verify, update, bulk reject, mark deadline, assign, publish)
- **New:** 13 steps (lock order, lock offer, fetch intent, 4 validations, amount/currency match, idempotency guard, update, bulk reject, mark deadline, assign, publish)
- **Reason:** Payment intent validation added per RISK-004

### ADDED — Section 13.2 (Modified Files)

- **Added:** `apps/payments/models.py` — Add nullable order_offer FK to PaymentIntent
- **Reason:** PaymentIntent model change for 1:N link

### MODIFIED — Section 13.2 (orders/models.py)

- **Previous:** "Add OrderOfferStatus, OrderOffer"
- **New:** "Add OrderOfferStatus, OrderOffer (remove payment_intent FK)"
- **Reason:** FK direction reversed
