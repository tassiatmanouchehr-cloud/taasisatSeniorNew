# Generic Service Marketplace Framework

**Module 04 — Service Execution & Session Lifecycle Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation (reference implementation of the Generic Service Marketplace Framework) |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine, Module 03 — Booking, Assignment & Service Activation Engine |
| **Next Modules** | Module 05/06 — Payment & Settlement, future Quality / Dispute / Reporting modules |
| **Language** | Persian business domain, English technical structure |

> Modules 01–03 are Frozen and Approved and are treated as baseline. Module 04 must not change their decisions unless a major architectural conflict is discovered.

> **Architecture Upgrade Notice:** starting with this module, the project is no longer designed as a single-purpose reference implementation platform. It is designed as a **Generic Service Marketplace Framework** (Layer 1 — Core Platform, domain-independent) with **Generic Service Marketplace Framework Reference Implementation as its first reference implementation** (Layer 2 — reference implementation Domain Mapping). Every section below states the Core Platform pattern first, then its reference implementation mapping.

# 26 — Test Scenarios

> Scope note: these cover the structural flows decided in Discovery. Legally sensitive crisis scenarios (death, serious accidents, insurance, force majeure) remain explicitly deferred and are not tested here.

## Session Lifecycle Tests
- TS-401: Session cannot start without an Active Assignment (BR-04-001).
- TS-402: Provider cannot move to PROVIDER_EN_ROUTE without GPS captured for reference implementation.
- TS-403: Session cannot enter IN_PROGRESS without passing the Start Checklist.
- TS-404: Provider can mark PROVIDER_COMPLETED but cannot close the session directly.
- TS-405: Session closes only after CUSTOMER_CONFIRMED or Operational Review resolution.
- TS-406: Early completion is allowed without a special exception.

## Presence & Location Tests
- TS-407: Arrival is only valid within the configured distance radius.
- TS-408: GPS problem report is accepted with required fields (reason, device status, note, timestamp).
- TS-409: Location mismatch applies the configured policy (block / allow-with-reason / etc.).
- TS-410: Unauthorized departure is classified correctly (temporary leave / unauthorized / review).
- TS-411: Location records are immutable; corrections only via administrative note.

## Start Checklist Tests
- TS-412: Session start requires presence + checklist + evidence + customer confirmation (or exception).
- TS-413: Uncooperative customer at start produces a recorded problem, not a silent block.

## Activity Tests
- TS-414: Every Activity belongs to exactly one Session.
- TS-415: Activities are immutable; only Correction/Review/Note can be appended.
- TS-416: Skipped activities still appear in the Timeline.

## Observation Tests
- TS-417: Every Observation has a required Actor.
- TS-418: Internal notes are never Customer-visible by default.
- TS-419: A critical observation can trigger a follow-up/operational-review event.

## Evidence Tests
- TS-420: Required evidence missing at a mandatory point produces `evidence_required_missing`.
- TS-421: Evidence records are immutable; disputes handled via Review/Flag/Rejection.
- TS-422: Evidence retention expires per configured duration.

## Interaction Tests
- TS-423: Every Interaction has a Session, Sender, and Recipient.
- TS-424: Interactions are never deleted; only Hidden/Archived/Flagged/Restricted.
- TS-425: A phone call is recorded as an event with duration, result, and follow-up flag.
- TS-426: Real phone numbers are never exposed between Customer and Provider.

## Exception Tests
- TS-427: Every Exception has an Owner and eventually a Resolution.
- TS-428: Exception state and Session state transition independently (BR-04-068).
- TS-429: Exceptions are never deleted, only closed.

## Extension Tests
- TS-430: Extension requires an active Session.
- TS-431: Extension is applied only with mutual agreement.
- TS-432: Unresolved extension disagreement routes to Operational Review.
- TS-433: Approved extension updates the session's expected end time and timeline.
- TS-434: Extension never creates an invoice.

## Completion & Handover Tests
- TS-435: Provider completes first; Customer confirms second.
- TS-436: Session completion does not close the Service Case (multi-session contract stays active).
- TS-437: Handover updates remaining sessions, progress, and next planned session.
- TS-438: Disputed completion routes through Operational Review before closing.
- TS-439: Session closure emits events only, never financial output.

## Boundary & Architecture Tests
- TS-440: Module 04 begins exactly at "Service Started" handed off from Module 03.
- TS-441: Module 04 never produces an invoice, settlement, or payout.
- TS-442: Core Platform schema contains no reference implementation-specific field names (domain isolation).
- TS-443: All ten sub-engines emit their events through a single EventBus consumed by Notification, Dashboards, and Module 05/06.

## Audit Tests
- TS-444: Every manual action (override, resolution, correction) records actor, role, timestamp, and reason.
