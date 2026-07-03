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

# 10 — Service Session Specification

## Purpose
Define the Service Session: one concrete scheduled occurrence of care within a Service Case, and the coordination choreography leading up to it.

## Business Goal
Make sure every scheduled visit — single or recurring — is actively tracked from confirmation through arrival, with automatic escalation if something stalls.

## Functional Specification

- The first Session is created immediately once timing is confirmed (BR-316); for a recurring Contract (from Module 01), the full session schedule is created at once.
- Coordination sequence per Session: reminder sent → provider signals en route → arrival check sent to customer → Service Started (FR-306, Flow 5).
- If the provider has not signalled "on the way" close to appointment time, the system immediately contacts the provider directly and involves the company if applicable (BR-318) — this is an active escalation, not a passive reminder.
- At appointment time, the customer/family is asked whether the provider arrived (BR-319), consistent with Module 01's arrival-check pattern.
- A Session's Module 03 responsibility ends exactly at "Service Started" (BR-331); every following action (care activities, checklists, reports) belongs to Module 04.

## Business Rules
See `03_BUSINESS_RULES.md` — BR-316 through BR-319, BR-331.

## Non-Functional Requirements
- Escalation timing (BR-318) and reminder timing (BR-317) must run as reliable scheduled jobs, not depend on a user having the app open.
- Session state must be visible live in customer/provider/company/Platform Owner dashboards (`16_UI_SCREEN_CATALOG.md`).

## Edge Cases (structural, non-legal)
- Provider signals en route but then goes silent before arrival — dashboard must reflect "en route, no update" distinctly from "arrived."
- Recurring contract: one session in the middle of the series fails to be confirmed — only that session is affected, not the whole schedule (consistent with Module 01's BR-132 single-session cancellation).

## Future Extension
- Live GPS-based ETA feeding directly into the en-route signal (explicitly deferred, per Module 01 discovery notes).
- Predictive delay flags based on provider's historical punctuality.

## Open Questions
- Exact minutes-before-appointment threshold for triggering BR-318 escalation is not numerically fixed; left as configurable default.

## Related ADR
ADR-03-05, ADR-03-09 (see `20_ADR.md`)

## Related Domain Objects
ServiceCase, ServiceAssignment, CoordinationEvent
