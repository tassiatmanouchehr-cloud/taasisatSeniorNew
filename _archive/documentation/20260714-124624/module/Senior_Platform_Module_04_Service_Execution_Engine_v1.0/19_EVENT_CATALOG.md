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

# 19 — Event Catalog

## Purpose
List every event Module 04 emits across its ten sub-engines, continuing the event-driven foundation established since Module 01 and formalized as a project-wide principle in `02_PLATFORM_ARCHITECTURAL_PRINCIPLES.md` (§5).

## Session Lifecycle Events
```text
session_ready_for_execution
provider_en_route
provider_location_captured
provider_arrived
arrival_verified
arrival_location_mismatch
start_check_started
start_check_completed
start_check_failed
session_started
session_in_progress
session_paused
session_resumed
session_interrupted
session_completed_by_provider
customer_confirmation_requested
customer_confirmation_pending
customer_confirmation_failed
operational_confirmation_requested
session_completion_confirmed_by_customer
session_closed
execution_completed
```

## Presence & Location Events
```text
provider_en_route_location_captured
provider_arrival_location_captured
provider_presence_verified
provider_presence_unverified
location_mismatch_detected
gps_unavailable_reported
manual_location_override_created
provider_departure_captured
unauthorized_departure_reported
presence_review_required
```

## Activity, Observation, Evidence Events (generic pattern)
```text
activity_created / activity_completed / activity_skipped / activity_failed
observation_recorded / warning_record_created / critical_value_detected
follow_up_required / operational_review_required
evidence_captured / evidence_attached / evidence_submitted
evidence_required_missing / evidence_rejected / evidence_flagged
evidence_review_requested / evidence_visibility_changed
```

## Interaction Events
```text
message_sent
message_received
issue_reported
help_requested
operational_call_requested
operational_call_completed
communication_escalated
communication_resolved
communication_closed
```

## Exception Events
```text
exception_created
exception_assigned
exception_updated
exception_evidence_added
exception_interaction_added
exception_resolved
exception_closed
```

## Extension / Overtime Events
```text
extension_requested
extension_approval_requested
extension_approved
extension_rejected
extension_disputed
extension_applied_to_session
extension_price_impact_recorded
extension_operational_review_required
extension_closed
```

## Completion & Handover Events
```text
session_closed
session_handed_over
service_case_updated
next_session_ready
customer_feedback_available
```

## Consumers
- Notification Engine (`20_NOTIFICATION_ENGINE.md`)
- Role Dashboards / UI (`24_UI_SCREEN_CATALOG.md`)
- Module 05/06 (subscribes to completion/handover events as its entry trigger)
- Audit log (every event persisted, per Platform Principle 18 — Audit by Design)

## Non-Functional Requirements
- Events are immutable (Platform Principle 5).
- Every event must carry enough context (session, actor, related entity) for a consumer to act without an extra lookup for the common case.
