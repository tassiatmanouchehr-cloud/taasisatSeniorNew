# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose

Module 07 defines the Communication Orchestration Engine for a generic service marketplace. Its responsibility is to transform platform events into governed, traceable, configurable, multi-recipient and multi-channel communications.

It supports:
- SMS
- Email
- Push notification
- Web notification
- Mobile notification
- In-app notification
- Persistent inbox
- Dashboard notification
- Chat and conversation
- Reminder
- Announcement
- Campaign and broadcast
- Webhook
- Optional voice call
- Future channels

## 2. Architectural Rule

Every meaningful action in the platform must emit a CES Event.

Every CES Event may produce:
- zero communications,
- one communication,
- many communications,
- different messages for different audiences,
- different channels for each audience,
- different templates by role, tenant, locale, intent, condition and priority.

No module is allowed to send communication directly.

## 3. High-Level Flow

```text
CES Event
  ↓
Event Listener
  ↓
Communication Policy Engine
  ↓
Rule Matcher
  ↓
Audience Resolver
  ↓
Channel Resolver
  ↓
Preference Resolver
  ↓
Template Resolver
  ↓
Delivery Job Engine
  ↓
Provider Adapter Layer
  ↓
Delivery Tracking
  ↓
Read/Open/Click Tracking
  ↓
Communication Audit + Timeline
```

## 4. Main Components

### Event Listener
Receives CES Events, validates schema, validates idempotency, identifies source module, event type, aggregate reference and tenant context.

### Communication Policy Engine
Determines whether an event should produce communication and which rules apply.

### Rule Matcher
Matches event type, tenant, actor, aggregate, audience, condition and priority to one or more active communication rules.

### Audience Resolver
Converts logical audiences into concrete recipients. Example: `customer`, `provider`, `organization_admins`, `platform_owner_team`.

### Channel Resolver
Determines active channels per recipient and rule.

### Preference Resolver
Applies framework defaults, platform policies, tenant overrides, role policies, user preferences and critical overrides.

### Template Resolver
Selects versioned channel-specific templates.

### Template Engine
Renders safe channel-specific payloads using approved event variables and approved data resolvers.

### Delivery Job Engine
Creates one job per recipient per channel.

### Provider Adapter Layer
Sends through external or internal channel providers without exposing provider details to business modules.

### Delivery Tracking
Tracks created, queued, sent, delivered, failed, read, opened, clicked, acknowledged and expired statuses.

### Communication Audit
Records every decision, skip, send, retry, failure and read event.

## 5. Activation / Deactivation Model

Communication can be enabled or disabled at these levels:

1. Framework default
2. Platform owner configuration
3. Tenant / organization configuration
4. Role-level configuration
5. Event-level configuration
6. Audience-level configuration
7. Channel-level configuration
8. Template-level configuration
9. User preference
10. Emergency override

Critical, financial, security, fraud, cancellation, legal and dispute messages must not be silently discarded. They may use fallback channels or mandatory audit-only behavior depending on legal and platform policy.

## 6. Communication Intent

Standard intents:
- informational
- transactional
- reminder
- operational
- financial
- security
- warning
- critical
- trust_and_safety
- support
- legal
- marketing
- system

Intent affects priority, channel selection, quiet-hours behavior, opt-out rules, retry frequency, escalation and audit depth.

## 7. Priority Model

Priority levels:
- critical
- high
- normal
- low

Priority affects queue, retry, provider selection, fallback, quiet-hour bypass and escalation.

## 8. Non-Responsibilities

Module 07 does not:
- create orders,
- create bookings,
- assign providers,
- calculate prices,
- collect payments,
- settle money,
- make trust decisions,
- change business entity lifecycle state,
- replace business audit logs,
- own business data.

It communicates what happened. It does not decide whether the original business action was valid.

## 9. Genericity Rule

The core module must never hard-code domain-specific roles. Reference implementations may map domain terms to generic roles.

Example mapping for reference-implementation reference only:
- customer/family → customer
- independent provider → provider
- company provider → provider under organization
- provider company → organization
- Platform Owner and team → platform_owner / platform_operator

## 10. Freeze Statement

Module 07 becomes enterprise-ready when every communication is event-driven, configurable, auditable, tenant-isolated, provider-abstracted, template-versioned and free from domain leakage.
