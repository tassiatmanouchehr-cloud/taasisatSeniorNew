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

# 20 — Architecture Decision Records

## ADR-03-01 — Selection Is Not Automatic Booking
A customer's selection creates a Selection Lock, not an immediate Confirmed Assignment; the responsible provider must still commit.

## ADR-03-02 — Three Structurally Separate Commitment Paths
Independent provider, company provider, and company package are implemented as distinct commitment strategies, not one generic path with conditionals (Decision 03-006).

## ADR-03-03 — Company Owns Company-Provider Commitment
For company providers, the company — not the individual provider — is the party whose acceptance confirms the Assignment.

## ADR-03-04 — Service Case as Aggregating Record
A Service Case aggregates all Assignments and Sessions for a request, supporting mixed per-need status during confirmation.

## ADR-03-05 — Sessions Created Eagerly from Confirmed Timing
The first Session (and the full recurring schedule, for contracts) is created as soon as timing is confirmed, not deferred to service start.

## ADR-03-06 — Assignment Created Only on Commitment
An Assignment record is created only after commitment succeeds, never at the moment of customer selection, to avoid falsely implying a booking exists.

## ADR-03-07 — No Redundant Confirmation Screen
Live dashboards in each role's own panel replace the need for a separate one-time booking-summary confirmation screen (scenario 1 decision).

## ADR-03-08 — Manual Hold Before Service Start
Platform Owner/support can hold a Service Case before it starts if risk is identified, with mandatory reason and audit (scenario 2 decision).

## ADR-03-09 — Active Escalation, Not Passive Reminder
Non-response near appointment time triggers immediate direct contact and company involvement rather than only another passive notification (scenario 3 decision, BR-318).

## ADR-03-10 — Event-Driven Continuity
Module 03 continues Module 01's event-driven foundation; all booking/coordination transitions are emitted as events for dashboards, notifications, and Module 04.

## ADR-03-11 — Boundary at Service Started
Module 03 ends exactly at the "Service Started" event (Decision 03-051); this boundary was chosen over ending earlier ("Ready to Start") specifically to keep arrival/delay/no-show handling on the pre-service side, before any care has actually happened.

## ADR-03-12 — Documentation Package Standard Upgrade
Starting with Module 03, documentation is produced as a 22-file versioned package with per-file headers (Depends On / Next Modules) and a fixed enriched section template (Purpose, Business Goal, Functional Specification, Business Rules, NFR, Edge Cases, Future Extension, Open Questions, Related ADR, Related Domain Objects), intended to be readable by both humans and coding agents.

## ADR-03-13 — Legal Crisis Scenarios Deferred, Not Invented
The ~100-item crisis/legal exception catalogue is explicitly excluded from this freeze rather than being filled in speculatively, since it requires legal review before being encoded as binding business rules.
