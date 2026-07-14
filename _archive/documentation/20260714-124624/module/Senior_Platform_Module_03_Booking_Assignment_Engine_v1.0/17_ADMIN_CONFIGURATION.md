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

# 17 — Admin Configuration

## Platform Owner Functions

### Configuration

- Selection Lock TTL (default to be tuned operationally)
- Provider commitment window (per path: independent provider / company provider / company package)
- Non-response escalation threshold (BR-318)
- Pre-appointment reminder timing (BR-317)
- Manual hold policy defaults
- Notification channel configuration for Module 03 events (extends Module 02's channel settings)

### Operational Control

- View all Service Cases and their status
- View all pending/failed commitments
- Place or release a manual hold
- Manually create or override an Assignment
- Manually extend a Selection Lock
- View full audit trail per Service Case
- View role dashboards in aggregate (crises, delays, no-shows, replacements)

## Support / Operator Functions

Subject to permission:

- View Service Case status
- Assist a customer through withdrawal or confirmation issues
- Place a hold if authorized
- Escalate a stalled commitment or coordination issue

## Forbidden Admin Behavior

- Silently substituting a provider without logging a reason (BR-330)
- Bypassing the audit trail
- Overriding a customer withdrawal without logged justification
- Skipping escalation (BR-318) for a silent provider

## Audit Requirements

Every manual action must record:

- actor
- role
- timestamp
- Service Case / Assignment
- action
- reason
- before/after state
