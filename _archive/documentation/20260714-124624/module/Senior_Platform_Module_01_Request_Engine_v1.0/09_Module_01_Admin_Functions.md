# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Admin Functions

## Platform Owner Functions

Platform Owner must have highest-level control over Module 01 settings.

### Configuration

- Configure selection reminder time (default 24h)
- Configure auto-delete / phone follow-up policy
- Configure publishing breadth (max notified recipients)
- Configure attachment size and compression limits
- Configure urgency handling
- Configure cancellation windows per role
- Toggle AI file classification
- Toggle future smart distribution when available

### Operational Control

- View all requests and their status
- View request timeline and full event history
- View applications per request
- View customer request history (including deletions)
- Manually intervene in stuck requests
- Review and action protection signals
- Reopen or reassign an auto-deleted request when justified

## Support / Operator Functions

Subject to permission:

- View request status and timeline
- Assist a family that cannot complete a request
- Make the follow-up phone call on no-selection timeout
- Escalate protection signals
- Coordinate replacement when a provider is unavailable mid-contract

## Forbidden Admin Behavior

- Exposing medical files beyond need-to-know scope
- Silently editing a customer's request without record
- Bypassing the audit trail
- Overriding cancellation penalties without a logged reason

## Audit Requirements

Every manual action must record:

- actor
- role
- timestamp
- request
- action
- reason
- before / after state
