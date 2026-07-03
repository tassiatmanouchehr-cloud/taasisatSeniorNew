# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Business Rules

## Request Start Rules

### BR-101 — Guided Entry
Request creation is step-by-step; the system asks questions progressively instead of showing one large form.

### BR-102 — Guest Building Allowed
A user can start and build a request without full registration.

### BR-103 — Identity at Final Step
Mobile number, verification code, and personal identity are captured at the last step before final submission.

### BR-104 — Service or Care-Receiver First
The flow may begin either by selecting a service or by describing the service recipient; both entry paths must lead to the same structured request.

## Information Collection Rules

### BR-105 — Form-First Interface
The primary interface is a traditional structured form.

### BR-106 — Rich Detail Allowed
The user may add free-text description, photos, and video in addition to structured fields.

### BR-107 — Attachment Limits
Attachments must be compressed and constrained by size to stay lightweight.

### BR-108 — User-Owned File Type
The AI may suggest a file's type, but the user confirms or corrects it; the system never finalizes a medical file type without user confirmation.

### BR-109 — Minimal Confirmation UX
File-type confirmation must be a single simple question with two actions: confirm or correct.

## Multi-Service-Need Rules

### BR-110 — Multiple Needs per Request
A request may contain more than one service need.

### BR-111 — Need-Level Structure
Each service need is stored as its own structured item inside the request so downstream matching can run per need.

## Validation Rules

### BR-112 — Sufficiency Check
A request must contain enough information (service, service recipient context, location, timing) before it can be published.

### BR-113 — Block Publish on Failure
If validation fails, the request stays in a pre-publish state and the user is told what is missing.

## Publishing Rules

### BR-114 — Need-to-Know Publishing
A request is shown only to providers who are eligible for it (service, coverage/city, availability, completeness), never to everyone.

### BR-115 — Targeted Notification Breadth
The system should not notify all eligible providers when the pool is large; it notifies a bounded, most-relevant subset. Breadth is configurable by Platform Owner.

### BR-116 — Provider New-Request Awareness
An eligible provider may see the count of new relevant requests (e.g. "7 new requests in Shiraz") before opening them.

### BR-117 — Behaviour Signals for Future Ranking
Provider behaviour (repeatedly viewing without applying, or applying but never being selected) is recorded as signal data for future ranking; it does not block anyone in MVP.

## Request Editing Rules

### BR-118 — Owner May Edit
The request owner may edit request information after creation.

### BR-119 — Edit After Provider Selected
If a provider is already selected and confirmed, that provider is notified first and must re-confirm the changed request.

### BR-120 — Edit While Applications Pending
If providers have applied but none is selected yet, applied providers in the queue are notified of the change.

### BR-121 — Address / Time Change Handling
A material change (such as address or time) follows the same rules as BR-119/BR-120 depending on whether a provider is already selected.

## Multi-Need Cancellation Rules

### BR-122 — Remove Single Need
For a multi-need request, the owner may remove a single service need without cancelling the whole request, choosing whichever path gives the simplest user experience.

## Deletion Rules

### BR-123 — Delete Before Acceptance
As long as no provider has been accepted, the owner may delete the request freely.

### BR-124 — Silent Deletion Notification
When a request is deleted before acceptance, other applied providers are not separately notified (they assume another provider was chosen), but the deletion is recorded in the customer profile.

### BR-125 — Deletion History
Every deletion is stored in the customer profile / request history.

## No-Selection Timeout Rules

### BR-126 — 24h Reminder
If the family does not select any provider within 24 hours, the system sends a message.

### BR-127 — Phone Follow-Up
If there is still no response after the reminder, the platform attempts a phone call.

### BR-128 — Auto-Delete with Retention
If the family still does not respond, the request is deleted but retained in the customer profile for history.

## Selected-Provider Follow-Up Rules

### BR-129 — Pre-Appointment Reminder
The selected provider is reminded roughly one hour before the appointment with the time and location.

### BR-130 — Arrival Check
At the appointment time, the customer is asked whether the provider arrived (and whether the provider called about a delay).

## Scheduling / Contract Rules

### BR-131 — Recurring is a Contract
A recurring need is modelled as a Contract that contains multiple sessions.

### BR-132 — Session-Level Cancellation
The owner may cancel a single session of a contract without cancelling the whole contract.

### BR-133 — Provider Unavailable Mid-Contract
If a provider cannot attend a session (e.g. illness), the company proposes a replacement, the platform assists, and the customer is kept informed.

## Cancellation Rules

### BR-134 — Who May Cancel
Family, customer, provider, company, and platform may all cancel, subject to timing and role rules.

### BR-135 — Cancellation Timing
Each role's cancellation window is policy-driven and configurable (exact windows to be tuned operationally).

### BR-136 — Repeated Provider Cancellation Penalty
A provider who repeatedly cancels accepted work is penalized.

### BR-137 — Repeated Customer Cancellation Penalty
A customer who repeatedly cancels after selecting a provider is penalized.

### BR-138 — Fair Process Over Absolute Rights
Neither customer nor provider is "always right"; the platform protects a fair process (see ADR-01-25).

## Platform Protection Rules

### BR-139 — Off-Platform Bypass Detection
The engine must detect attempts to move the deal off-platform: sharing a phone number in chat, writing a number on a photo or inside a PDF, or agreeing on price outside the site.

### BR-140 — Cancel-After-Arrival Abuse
The engine must guard against a provider arriving and then asking the customer to cancel the order to avoid commission.

### BR-141 — Protection is a First-Class Concern
Off-platform bypass is treated as a business risk, not an accident, and every request carries protection triggers from creation onward.

## Timeline & Event Rules

### BR-142 — Request Timeline Required
Every request keeps a chronological timeline of its important events.

### BR-143 — Role-Filtered Timeline
Each role sees only the timeline entries it is permitted to see.

### BR-144 — Events Drive the System
Request actions (created, applied, updated, confirmed, reminded, arrived, completed, cancelled) are emitted as events that downstream modules consume.

## Boundary Rules

### BR-145 — Handoff to Matching
When a request is validated and published, matching (Module 02) takes over provider evaluation and presentation.

### BR-146 — No Downstream Ownership
Module 01 does not perform ranking, payment, or final settlement.
