# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Admin Functions

## Platform Owner Functions

Platform Owner must have highest-level control over Module 02 settings.

### Configuration

- Change distribution strategy
- Enable/disable Push, SMS, Email, In-App notifications
- Configure fallback rules
- Configure reminder time, default 24h
- Configure expiry time, default 48h
- Configure ranking weights
- Configure company operational bonus
- Configure future AI ranking toggle when available

### Operational Control

- View all match rounds
- View eligibility reasons
- View accepted/rejected/withdrawn candidates
- Reopen expired matching
- Restart matching
- Rerank candidates
- Suggest candidate transparently
- Directly invite a provider/company to matching
- View audit logs

## Support / Operator Functions

Subject to permission:

- View match status
- View customer-visible candidate list
- Rerun ranking if authorized
- Restart matching if authorized
- Suggest candidate if authorized
- Contact customer/provider outside module if operationally needed

## Forbidden Admin Behavior

- Hidden ranking manipulation
- Showing suspended providers to customers
- Selecting a provider on behalf of customer without explicit authorized process
- Bypassing audit logs

## Audit Requirements

Every manual action must record:

- actor
- role
- timestamp
- request
- match round
- action
- reason
- before/after state
