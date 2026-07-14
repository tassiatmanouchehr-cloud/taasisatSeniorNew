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

# 04 — Business Rules

> Rule numbering follows the actual Discovery session. BR-04-021 through BR-04-028 were intentionally left unassigned in Discovery (the Start Checklist Engine's rules were discussed structurally but not individually numbered) — see `11_START_CHECKLIST_ENGINE.md` for its descriptive rules instead.

## Session Lifecycle Rules

### BR-04-001 — Session Must Start Only After Assignment Activation
A Session can only execute once its Assignment is Active (handoff from Module 03).

### BR-04-002 — Provider Must Declare En Route
The provider must declare en route before arrival.

### BR-04-003 — GPS Required for reference implementation En Route / Arrival
GPS is mandatory at en-route and arrival time for reference implementation; configurable for the Core Platform.

### BR-04-004 — Session Cannot Start Without Start Validation
A Session cannot enter IN_PROGRESS without passing the Start Checklist.

### BR-04-005 — Provider Records Are Immutable
All provider reports, observations, activities, and evidence are immutable after recording.

### BR-04-006 — Provider Cannot Close Session Alone
The provider can only mark a Session Completed; final closing requires Customer confirmation or Operational Review resolution.

### BR-04-007 — Customer Confirmation Required
Completion must be confirmed by the Customer; if the Customer cannot confirm, the case enters Operational Confirmation.

### BR-04-008 — Early Completion Is Allowed
If work finishes early, the provider may complete the Session; no special exception is required.

### BR-04-009 — Overtime Requires Mutual Agreement
Time extension is only valid with agreement between Provider and Customer; without agreement, Organization or Platform Team intervenes.

### BR-04-010 — Financial Logic Is Out of Scope
Module 04 produces no invoice, settlement, or payout — only execution events.

## Presence & Location Rules

### BR-04-011 — Location Capture Is Configurable in Core
In the Core Platform, GPS and location capture are configurable by Service Type, Organization, Request, Session Risk Level, and Customer Preference.

### BR-04-012 — Location Capture Is Mandatory for reference implementation
In reference implementation, location is mandatory when the provider declares en route, declares arrival, requests session start, and records session completion.

### BR-04-013 — En Route Requires GPS
A provider cannot move to PROVIDER_EN_ROUTE without location being captured.

### BR-04-014 — Arrival Requires Distance Validation
Arrival is only valid within an acceptable radius of the service address (configurable; reference implementation default 100–300 meters).

### BR-04-015 — Location Mismatch Does Not Always Block
On GPS mismatch, behavior is configurable: BLOCK_START, ALLOW_WITH_REASON, ALLOW_WITH_CUSTOMER_CONFIRMATION, ALLOW_WITH_ORGANIZATION_APPROVAL, or SEND_TO_OPERATIONAL_REVIEW.

### BR-04-016 — Provider Can Report GPS Problem
If GPS fails, the provider may report the problem with reason, device status, manual note, optional photo, optional customer confirmation, and timestamp.

### BR-04-017 — Presence Records Are Immutable
All location records are immutable; correction happens only via administrative note or audit record.

### BR-04-018 — Unauthorized Departure Must Be Detected or Reported
A mid-session departure is classified as temporary leave (authorized), unauthorized departure (not authorized), or operational review (unclear).

### BR-04-019 — Continuous Tracking Is Not Required by Default
The system does not need to continuously track the provider; event-based location capture at key points (en route, arrived, start, pause, resume, temporary leave, completion, checkout) is sufficient.

### BR-04-020 — Manual Override Requires Audit
Organization or Platform Team may override location validation only with reason, actor, role, timestamp, affected session, and audit trail.

## Execution Activity Rules

### BR-04-029 — Activity Belongs to One Session
Every Activity belongs to exactly one Session.

### BR-04-030 — Activity Cannot Exist Outside a Session
An Activity cannot be created outside a Session context.

### BR-04-031 — Activity Requires an Actor
Every Activity must have an actor: Provider, Customer, Organization, Platform Team, or System.

### BR-04-032 — All Activities Enter the Timeline
No Activity exists outside the Timeline.

### BR-04-033 — Activities Are Immutable
Activities cannot be edited; only Correction, Review, or Administrative Note can be appended.

### BR-04-034 — Activity May Have Evidence
An Activity can carry Evidence (photo, video, audio, signature, file); Evidence itself is owned by its own engine.

### BR-04-035 — Activity May Produce Observation
An Activity can produce an Observation (e.g. blood pressure, temperature, pain score); Observation itself is owned by its own engine.

### BR-04-036 — Activity May Produce Event
An Activity can produce an Event, which may then produce a Notification, Timeline entry, and Audit event.

## Observation & Notes Rules

### BR-04-037 — Observations Belong to Session
Every Observation is recorded inside exactly one Service Session.

### BR-04-038 — Actor Is Required
Every Observation must have a defined actor: Provider, Customer, Organization, Platform Team, or System.

### BR-04-039 — Records Are Immutable
Observations and Notes never change after recording; Correction is only added as a new record.

### BR-04-040 — Visibility Must Be Explicit
Every Record must declare a visibility level: Customer Visible, Provider Visible, Organization Visible, Platform Internal, Private To Actor, or Custom.

### BR-04-041 — Domain Meaning Lives Outside Core
Core only holds the structure; the meaning of a record is defined in the implementation (e.g. `type=MEASUREMENT, field_key=blood_pressure` is just a measurement in Core, a customer's blood pressure in reference implementation).

### BR-04-042 — Measurement Units Must Be Versioned
Every Measurement must define unit, unit_system, value_type, and normal_range_reference.

### BR-04-043 — Critical Observations May Trigger Events
Some observations can trigger events, e.g. `warning_record_created`, `critical_value_detected`, `follow_up_required`, `operational_review_required`.

### BR-04-044 — Internal Notes Must Never Be Customer Visible By Default
Internal notes from Organization or Platform Team are not shown to the Customer by default.

## Evidence Rules

### BR-04-046 — Evidence Is Configurable
Evidence is not always mandatory; it is configurable by Service Type, Organization, Request, Session, Risk Level, and phase (Start / During / Completion).

### BR-04-047 — Evidence May Be Required or Optional
Every Evidence Rule can be REQUIRED, OPTIONAL, CONDITIONAL, or NOT_ALLOWED.

### BR-04-048 — Evidence Records Are Immutable
After recording, the original file and metadata never change and cannot be directly deleted; only review, correction note, rejection reason, administrative flag, or audit note can be added.

### BR-04-049 — Evidence Must Belong to a Context
Every Evidence item must attach to one of: Session, Activity, Observation, Checklist Item, Completion Request, Exception Case, or Operational Review.

### BR-04-050 — Evidence Visibility Must Be Controlled
Every Evidence item has a visibility level: Customer Visible, Provider Visible, Organization Visible, Platform Internal, or Restricted.

### BR-04-051 — Evidence Should Not Become Medical Archive
In reference implementation, Evidence must not become a medical or clinical archive; it exists only to prove operation, confirmation, dispute, quality, or reporting needs.

### BR-04-052 — Evidence Retention Must Be Configurable
Retention duration is configurable (30/90/180 days, 1 year, custom); legal hold is explicitly deferred to a future module.

## Interaction Rules

### BR-04-053 — Interaction Belongs to a Session
Every Interaction belongs to a Session.

### BR-04-054 — Sender Required
Every Interaction (message) must have a defined sender.

### BR-04-055 — Recipient Required
Every Interaction (message) must have a defined recipient.

### BR-04-056 — All Interactions Enter the Timeline
No Interaction exists outside the Timeline.

### BR-04-057 — All Interactions Are Audited
Every message/interaction carries an audit trail.

### BR-04-058 — Interactions Are Not Deleted
Interactions are never deleted; if necessary, they become Hidden, Archived, Flagged, or Restricted.

### BR-04-059 — Phone Calls Are Also Events
A phone call (e.g. "Organization called Customer") is recorded as an event with duration, result, and follow-up-required flag.

### BR-04-060 — Resolved Communication Closes
If an issue is resolved, the related Interaction/Communication thread moves to Closed.

## Exception & Resolution Rules

### BR-04-061 — Exception Belongs to a Session
Every Exception must relate to a Session.

### BR-04-062 — Exception Requires an Owner
Every Exception must have an owner: Organization or Platform Team.

### BR-04-063 — Exception Requires a Resolution
Every Exception must have a resolution, even if the resolution is "No Action Required."

### BR-04-064 — Exception May Have Evidence
An Exception can carry supporting Evidence.

### BR-04-065 — Exception May Have Multiple Interactions
An Exception can have several related Interactions.

### BR-04-066 — Exception Enters the Timeline
Every Exception enters the Timeline.

### BR-04-067 — Exception Is Not Deleted
Exceptions are never deleted; only closed.

### BR-04-068 — Session State and Exception State Are Independent
If an Exception affects a Session, the Session's state machine and the Exception's state machine are managed independently (e.g. Session = IN_PROGRESS while Exception = UNDER_REVIEW, or Session = PAUSED while Exception = OPEN).

## Extension & Overtime Rules

### BR-04-069 — Extension Requires Active Session
An Extension can only be recorded while the Session is active.

### BR-04-070 — Extension Requires Mutual Agreement
A time extension is only valid with agreement between Customer and Provider.

### BR-04-071 — Price Impact Must Be Explicit
If an Extension has financial impact, it must be explicitly recorded as No Extra Cost, Extra Cost Agreed, Price To Be Reviewed, or Disputed — though the financial calculation itself is out of Module 04's scope.

### BR-04-072 — No Agreement Means Operational Review
If Customer and Provider do not agree, Organization or Platform Team intervenes.

### BR-04-073 — Extension Record Is Immutable
Once an Extension decision is recorded, the original record never changes; correction happens only via a new record.

### BR-04-074 — Extension Must Update Session Plan
An approved Extension updates the session plan: expected end time, planned duration, timeline, and event log.

### BR-04-075 — Extension Does Not Create Invoice
Module 04 creates no invoice or payment for an Extension — only events for future financial modules.

## Completion & Handover Rules

### BR-04-076 — Provider Completes First
The Provider records completion first.

### BR-04-077 — Customer Confirms Completion
The Customer confirms completion; if unable, the case enters Operational Review.

### BR-04-078 — Completion Does Not Automatically Close Case
Session completion does not mean the Service Case is finished (e.g. Session #5 of 30 completes; the Service Case remains active). This is one of the module's most important architectural rules.

### BR-04-079 — Handover Updates Service Case
On session close, the Service Case must be updated: remaining sessions, progress, next planned session, completion statistics.

### BR-04-080 — Session Closure Produces Domain Events
Closing a Session only produces events: `session_closed`, `session_handed_over`, `service_case_updated`, `next_session_ready`, `customer_feedback_available`.

### BR-04-081 — Financial Processing Starts After Module 04
Completion only produces an event; Module 05 decides invoice, settlement, payment, and payout.

## Boundary Rules

### BR-04-082 — Handoff at Service Started
Module 04 begins exactly at the "Service Started" event handed off by Module 03.

### BR-04-083 — No Payment Ownership
Module 04 does not own payment, invoicing, settlement, or payout logic (see BR-04-010, BR-04-075, BR-04-081).

### BR-04-084 — Legal Crisis Scenarios Deferred
Death, serious accidents, insurance, force majeure, and complex legal exception scenarios remain explicitly deferred pending legal review.
