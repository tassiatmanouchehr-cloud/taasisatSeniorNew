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

# 18 — Completion & Handover Engine (Primary)

## Purpose
Own the formal end of a Service Session and its handover to whatever comes next — not just "record that it's done," but determine whether it's really finished, confirmed, disputed, reviewable, closable, and what it means for the Service Case going forward.

## Business Goal
Make sure "session completed" always resolves to a clear, agreed, auditable outcome, and never quietly implies more than it should (like the whole contract or payment being done).

## Functional Specification

### Completion Lifecycle
```text
PROVIDER_COMPLETED → CUSTOMER_CONFIRMATION_PENDING → CUSTOMER_CONFIRMED → SESSION_CLOSED → HANDOVER_COMPLETED
```
Exception path:
```text
PROVIDER_COMPLETED → DISPUTED → OPERATIONAL_REVIEW → RESOLVED → SESSION_CLOSED
```

### Handover
This concept did not exist in Module 03. Once a Session ends, the engine determines what happens to the Service Case: is the case finished? Is there a next session? Does the weekly plan continue? Is the Assignment still active?

### Handover Targets
```text
Service Session → Service Case → Weekly Plan → Next Session → Assignment → Future Financial Modules → Reporting Modules
```

## Business Rules
BR-04-076 through BR-04-081 (see `04_BUSINESS_RULES.md`). The single most important rule is **BR-04-078**: completing one session never automatically closes the Service Case (e.g. Session #5 of a 30-session contract completes; the Service Case remains active) — and **ADR-04-012**: Session Completion is not Business Completion.

## reference implementation Implementation
Family requests one extra hour → agreed → planned Service Session time updated; a single Service Session in a 30-session plan finishes → the overall care plan continues; family gives feedback and rating at session end.

## Non-Functional Requirements
- Handover must always update the Service Case's remaining-sessions/progress/next-session data on close (BR-04-079).
- Closure must only ever emit events — never trigger financial side effects directly (BR-04-081).

## Edge Cases (structural, non-legal)
- Completion disputed by the customer — routes through DISPUTED → OPERATIONAL_REVIEW → RESOLVED before the session can close, rather than allowing an unresolved dispute to silently close.
- Last session of a multi-session plan closes — Handover must correctly signal "no next session" distinctly from "next session ready," since both are valid Service Case states.

## Future Extension
- Automated case-completion detection once all planned sessions are closed (not built in v1; currently a manual/derived read from the Service Case).

## Open Questions
- None explicitly raised beyond the future automation note above.

## Related ADR
ADR-04-012 (see `28_ADR.md`) — the most important ADR in this section.

## Related Domain Objects
CompletionRecord, HandoverRecord, ServiceSession, ServiceCase (Module 03)
