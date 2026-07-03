# Generic Service Marketplace Framework

**Module 03 — Booking, Assignment & Service Activation Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine |
| **Next Modules** | Module 04 — Service Execution / Care Delivery Engine, Module 05/06 — Payment & Settlement |
| **Language** | Persian business domain, English technical structure |

> Module 01 and Module 02 are Frozen and Approved and are treated as baseline. Module 03 must not change their decisions unless a major architectural conflict is discovered.

# 03 — Business Rules

## Selection Lock Rules

### BR-301 — Lock on Selection
The moment a customer/family selects a candidate, Module 03 receives and manages a Selection Lock for that Service Need or package.

### BR-302 — Lock Has a Validity Window
A Selection Lock is valid for a configurable window (default TTL set by Platform Owner; see `17_ADMIN_CONFIGURATION.md`).

### BR-303 — Lock Expiry Releases the Option
If the lock expires before provider commitment, the option is released and the request returns toward Matching / operator attention, and the customer is notified.

### BR-304 — Single Active Lock
Only one active Selection Lock may exist per Service Need at a time; a second concurrent selection attempt is rejected (consistent with Module 02's ADR-02 selection-lock behavior).

## Final Confirmation Rules

### BR-305 — No Redundant Confirmation Screen
Customer and provider status is visible live inside each party's own panel; a separate mandatory "confirm the summary" screen is not required in MVP.

### BR-306 — Terms Visible Before Commitment
Price/price range, timing, address, and cancellation terms must be visible to both customer and provider before provider commitment is finalized.

## Provider Commitment Rules

### BR-307 — Independent Provider Commits Personally
For an independent provider, the commitment obligation is personal; the provider must accept before the Assignment is Confirmed.

### BR-308 — Company Provider Commitment Owned by Company
When the customer selects a company provider, the company — not only the provider — owns the commitment.

### BR-309 — Company May Substitute a Company Provider
A company may substitute the assigned provider under company-controlled rules; a substitution must trigger a notice appropriate to how far along the booking is (informational if early, re-confirmation if the customer already has a specific-person expectation).

### BR-310 — Company Package Assignment
When the customer selects "company as package," the company assigns provider(s) itself. The company may assign any eligible provider; the customer does not need to approve each individual provider for MVP, but is informed who is coming.

### BR-311 — Three Paths Are Structurally Separate
Independent provider, company provider, and company package must be implemented as three distinct commitment flows, not one generic flow with conditionals bolted on (Decision 03-006).

## Assignment Creation Rules

### BR-312 — Assignment Created on Commitment
A Service Assignment is created only after the responsible party's commitment is confirmed, not at the moment of customer selection.

### BR-313 — Assignment Plan for Multi-Need Requests
A request with multiple service needs produces multiple linked Assignments, grouped as an Assignment Plan.

### BR-314 — Assignment Linked to Service Need
Every Assignment is linked to exactly one Service Need (or to a package covering several needs, explicitly recorded as such).

## Booking / Service Case Rules

### BR-315 — Service Case Creation
A Service Case is created once at least one Assignment in the plan is confirmed; a multi-need Service Case can have Assignments in different states simultaneously.

### BR-316 — Session Created from Confirmed Timing
The first Service Session is created immediately once timing is confirmed; for a recurring Contract (Module 01), the full session schedule is created.

## Pre-Service Coordination Rules

### BR-317 — Pre-Appointment Reminder
The provider is reminded ahead of the appointment (baseline consistent with Module 01's ~1h reminder; exact timing configurable).

### BR-318 — Non-Response Escalation
If the provider has not indicated "on the way" close to appointment time, the system immediately calls/contacts the provider and involves the company (if the provider is company-affiliated), rather than only sending a passive notification.

### BR-319 — Arrival Check
At appointment time, the customer/family is asked whether the provider arrived, consistent with Module 01's arrival-check pattern.

## Failure & Recovery Rules

### BR-320 — Provider Non-Acceptance
If the responsible party (provider or company) does not accept within the commitment window, the Assignment fails and the Service Need returns to Matching / operator attention.

### BR-321 — Provider Late Response
A late response after the window closes is rejected; the customer is not left waiting indefinitely.

### BR-322 — Customer Withdrawal Before Service Start
The customer may withdraw before service starts, subject to Module 01's cancellation rules and any applicable penalty.

### BR-323 — Company Changes Assigned Provider
A company may replace the assigned provider before service start under BR-309; if the customer had a specific-person expectation, the customer must be informed and may object through support.

### BR-324 — Scheduling Conflict
If a scheduling conflict emerges after commitment (e.g. provider double-booked), the system triggers replacement handling rather than allowing a silent conflict.

### BR-325 — Lock Expiry Handling
See BR-303; expiry always results in release plus customer notification, never a silent drop.

## Manual Intervention Rules

### BR-326 — Platform Owner Can Hold a Case
Platform Owner/authorized support can place a Service Case on hold before service start if documents, suspension, complaints, or repeated cancellations raise concern.

### BR-327 — Hold Requires Reason and Audit
Every hold action is logged with actor, reason, and timestamp.

### BR-328 — Manual Assignment / Override
Authorized staff may manually create or change an Assignment, extend a Selection Lock, or override a stalled booking, always transparently and with an audit trail (consistent with Module 02's no-hidden-manipulation principle).

## Audit & Traceability Rules

### BR-329 — Who Selected, Who Confirmed, Who Assigned
Every Service Case must retain who selected, who confirmed (customer side and provider side), who created the Assignment, and who intervened manually.

### BR-330 — Why Provider Changed
Any provider substitution records a reason.

## Boundary Rules

### BR-331 — Handoff at Service Start
Module 03 ends exactly at the "Service Started" event (Decision 03-051); Module 04 owns everything from that point.

### BR-332 — No Payment Ownership
Module 03 does not own payment, commission, or settlement logic.

### BR-333 — No Care Delivery Ownership
Module 03 does not own daily care reports, vitals, or care checklists.
