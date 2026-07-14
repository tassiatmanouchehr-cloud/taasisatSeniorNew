# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Architecture Decision Records

## ADR-01-01 — Request Engine is a Workflow Engine
Module 01 is modelled as a workflow engine over a request's life, not a static order form.

## ADR-01-02 — Step-by-Step Creation
Requests are built through a guided, progressive flow.

## ADR-01-03 — Guest Start, Late Identity
Users may build a request as a guest and identify only at the final step.

## ADR-01-04 — Form-First with Rich Attachments
The interface is a traditional form that also accepts text, photo, and video.

## ADR-01-05 — Compressed, Size-Limited Media
Attachments are compressed and bounded to protect performance.

## ADR-01-06 — AI Suggests, User Confirms File Type
AI classification is assistive; the user owns the final file type, reducing medical-data risk.

## ADR-01-07 — Multi-Service-Need Requests
A request may hold multiple service needs stored separately.

## ADR-01-08 — Validate Before Publish
A request must be sufficient before it can be published.

## ADR-01-09 — Need-to-Know Publishing (Principle 1)
The platform shows the right information to the right people at the right time, only as much as needed.

## ADR-01-10 — Targeted / Bounded Distribution
Publishing notifies a bounded most-relevant subset, not all eligible providers.

## ADR-01-11 — Provider Behaviour as Future Signal
View/apply behaviour is recorded for future ranking, not used to block in MVP.

## ADR-01-12 — Defined Request Life Cycle
Requests follow an explicit status machine from Draft to Completed / Cancelled.

## ADR-01-13 — Controlled Editing
Editing after creation triggers re-confirmation or re-notification based on status.

## ADR-01-14 — Single-Need Removal
An owner may remove one service need without cancelling the whole request.

## ADR-01-15 — Free Deletion Before Acceptance
Deletion is unrestricted until a provider is accepted, and always recorded.

## ADR-01-16 — Silent Deletion Notification
Applicants are not separately notified on pre-acceptance deletion.

## ADR-01-17 — No-Selection Timeout Ladder
24h reminder → phone call → auto-delete with retention.

## ADR-01-18 — Selected-Provider Follow-Up
~1h pre-appointment reminder plus an arrival check to the customer.

## ADR-01-19 — Recurring is a Contract
Recurring needs are a Contract of Sessions, separate from a single order.

## ADR-01-20 — Session-Level Cancellation
A single session can be cancelled without cancelling the contract.

## ADR-01-21 — Mid-Contract Replacement
Provider unavailability triggers company replacement plus platform assistance and customer notice.

## ADR-01-22 — Everyone-Can-Cancel with Penalties
All roles can cancel under timing rules; repeated abuse is penalized.

## ADR-01-23 — Platform Protection Engine at Request Time
Off-platform bypass detection begins the moment a request exists.

## ADR-01-24 — Event-Driven Foundation
Request actions are emitted as events that downstream modules consume.

## ADR-01-25 — Platform First (Principle 2)
Neither customer-first nor provider-first; the platform protects a fair process. No one is always right; a fair process is always right.

## ADR-01-26 — Role-Filtered Timeline
Every request keeps a timeline shown to each role only for permitted entries.

## ADR-01-27 — GPS Deferred
Live GPS is intentionally postponed to a later phase.

## ADR-01-28 — Discovery-First, No Early Product Bible
Module output is Journal + Business Decisions + Architecture Notes + Handover; a Product Bible is written only after ~80% of engines are designed.

## ADR-01-29 — Four Freeze Criteria
A module freezes only when Business Complete, Edge Cases Complete, Enterprise Ready, and Future Ready are all met.
