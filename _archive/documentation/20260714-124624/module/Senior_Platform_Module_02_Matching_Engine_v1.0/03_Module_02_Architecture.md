# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Architecture

## 1. Architectural Style

Module 02 is designed as a layered, strategy-based, explainable matching subsystem.

## 2. Main Pipeline

```text
Module 01 Request Engine
        ↓
Eligibility Engine
        ↓
Matching Engine
        ↓
Fitness Evaluation
        ↓
Ranking Engine
        ↓
Candidate Presentation Layer
        ↓
Recommendation Engine (reserved)
        ↓
Customer / Family Selection
        ↓
Module 03 Reservation / Contract / Payment
```

## 3. Eligibility Engine

Determines whether a provider is allowed to receive a request.

It answers:

```text
Eligible / Not Eligible / Eligible With Warning
```

It must also return reasons.

### Eligibility Categories

- Identity eligibility
- Verification eligibility
- Service eligibility
- Geographic eligibility
- Schedule eligibility
- Capacity/availability eligibility
- Policy eligibility
- Request-specific eligibility

## 4. Matching Engine

Builds valid matching options from eligible providers.

Candidate result types:

- `INDEPENDENT_PROVIDER`
- `ORGANIZATION_PROVIDER`
- `COMPANY`
- `INDIVIDUAL_PACKAGE`
- `ORGANIZATION_PACKAGE`
- `MIXED_SELECTION_OPTION`

## 5. Fitness Evaluation

Fitness measures suitability, not permission.

Examples:

- 100%: full coverage
- 70%: partial schedule coverage
- lower score: warnings present

## 6. Ranking Engine

Version 1 uses configurable rule-based scoring.

Future versions can plug in AI-assisted ranking.

## 7. Candidate Presentation Layer

Responsible for showing accepted candidates in a usable, trustworthy, comparable format.

## 8. Recommendation Engine

Reserved for future. It explains suggested choices rather than merely sorting.

## 9. Distribution Strategy

MVP:

```text
BROADCAST
```

Future:

```text
WAVE_BASED
SMART_DISTRIBUTION
```

## 10. Notification Strategy

All channels are configurable:

- Push
- SMS
- Email
- In-App
- Future WhatsApp / IVR / Auto Call

## 11. Manual Intervention

Manual intervention is transparent, permission-controlled, and audited.

## 12. Performance Approach

To avoid slowness:

- Precompute provider and service eligibility when provider data changes.
- Use indexed fields for status, service, location, and availability.
- Avoid heavy document checks during live matching.
- Cache frequently used provider profile summaries.
- Use background jobs for notification retries and document expiry alerts.

## 13. Module Boundary

Module 02 ends when a customer/family selection is recorded.

Module 03 owns final reservation, contract, payment, and assignment.
