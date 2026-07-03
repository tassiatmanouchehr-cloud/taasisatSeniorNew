# CHANGELOG

## v1.0 — Initial Freeze

- Upgraded project architecture from single-purpose reference implementation platform to a two-layer Generic Service Marketplace Framework (Core Platform + reference implementation Domain Mapping) — ADR-04-013.
- Defined Module 04 start boundary (Service Started, handed off from Module 03) and end boundary (Session Closed & Handed Over, events only).
- Decomposed Module 04 into ten sub-engines: five Primary (Session Lifecycle, Activity, Interaction, Exception & Resolution, Completion & Handover) and five Supporting (Presence & Location, Start Checklist, Observation & Notes, Evidence, Extension & Overtime) — ADR-04-014.
- Designed full state machines for Session Lifecycle, Presence & Location, Evidence, Interaction, Exception, Extension, and Completion & Handover.
- Established BR-04-001 through BR-04-084 covering all ten sub-engines (BR-04-021–028 intentionally left unassigned in Discovery for the Start Checklist Engine; documented descriptively instead).
- Recorded major architecture decisions: Immutable Execution Records (ADR-04-001), Event-Based Location Tracking (ADR-04-002), Platform-Controlled Communication (ADR-04-008), Universal Interaction Architecture (ADR-04-009), Independent Exception Lifecycle (ADR-04-010), Mutual-Agreement Extensions (ADR-04-011), Session Completion ≠ Business Completion (ADR-04-012).
- Authored the project-wide "constitution": Platform Architectural Principles v1.0, applying to Module 01+ and all future modules.
- Explicitly deferred legal/crisis exception scenarios (death, serious accidents, insurance, force majeure) and continuous live tracking.
- Generated standard ZIP package: `Generic Service Marketplace_Platform_Module_04_Service_Execution_Engine_v1.0.zip`.
