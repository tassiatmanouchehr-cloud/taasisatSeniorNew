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

# 22 — API Contract

> Contracts are conceptual. Final endpoint naming depends on implementation stack.

## Provider APIs

### POST /sessions/{session_id}/en-route
Declares en route; requires GPS (mandatory for reference implementation).

### POST /sessions/{session_id}/arrived
Declares arrival; requires GPS and triggers distance validation.

### GET /sessions/{session_id}/start-checklist
Returns the applicable checklist (generic + service-type + organization + risk-based).

### POST /sessions/{session_id}/start-checklist/submit
Submits checklist item responses/evidence.

### POST /sessions/{session_id}/start
Moves session to IN_PROGRESS once all start requirements pass.

### POST /sessions/{session_id}/activities
Records an Execution Activity.

### POST /sessions/{session_id}/observations
Records an Observation / Note / Measurement.

### POST /sessions/{session_id}/evidence
Uploads an Evidence item tied to a context.

### POST /sessions/{session_id}/pause
Pauses the session with a reason.

### POST /sessions/{session_id}/resume
Resumes a paused session.

### POST /sessions/{session_id}/report-issue
Creates an Exception.

### POST /sessions/{session_id}/request-support
Creates a HELP_REQUEST Interaction.

### POST /sessions/{session_id}/request-extension
Creates an ExtensionRequest.

### POST /sessions/{session_id}/complete
Records PROVIDER_COMPLETED with completion note/checklist/evidence.

## Customer APIs

### GET /sessions/{session_id}
Returns live session status (dashboard view).

### POST /sessions/{session_id}/confirm-completion
Records CUSTOMER_CONFIRMED with optional rating/feedback.

### POST /sessions/{session_id}/dispute-completion
Records a completion dispute → routes to Operational Review.

### POST /sessions/{session_id}/extension-requests/{id}/respond
Approves or rejects a counterpart's extension request.

### POST /sessions/{session_id}/interactions
Sends a message/interaction inside the session (platform-mediated).

## Organization APIs

### GET /organization/sessions/today
Dashboard of today's sessions across the organization's providers.

### POST /organization/sessions/{session_id}/override-location
Manual location override (audited).

### POST /organization/exceptions/{exception_id}/assign
Assigns/claims ownership of an Exception.

### POST /organization/exceptions/{exception_id}/resolve
Records an Exception resolution.

### POST /organization/sessions/{session_id}/extension-requests/{id}/resolve
Resolves a disputed/unresolved extension via Operational Review.

## Admin (Platform Team) APIs

### PATCH /admin/execution/settings
Updates GPS requirement, distance radius, evidence requirements, checklist templates, extension timeout.

### GET /admin/sessions/{session_id}/audit
Returns full audit trail.

### POST /admin/sessions/{session_id}/operational-review
Places or resolves an operational review on a session.

### GET /admin/exceptions
Lists exceptions by severity/status/owner.

## Internal Services

### SessionLifecycleService.transition(session, newState)
Enforces the Session Lifecycle state machine.

### PresenceService.capture(session, capturePoint, location)
Captures a location event; validates distance; applies mismatch policy.

### StartChecklistService.evaluate(session)
Evaluates whether all required checklist items and evidence are satisfied.

### ActivityService.record(session, activity)
Records an immutable Execution Activity.

### ObservationService.record(session, observation)
Records an immutable Observation; checks for critical-value triggers.

### EvidenceService.attach(context, evidence)
Attaches immutable Evidence to a context; enforces requirement rules.

### InteractionService.create(interaction)
Creates and routes an Interaction through its lifecycle.

### ExceptionService.create(session, exception)
Creates an independent Exception with its own lifecycle.

### ExtensionService.request(session, extension)
Runs the mutual-agreement Extension workflow.

### CompletionService.complete(session)
Runs the two-sided completion + handover workflow.

### EventBus.emit(event)
Emits Module 04 domain events (see `19_EVENT_CATALOG.md`).
