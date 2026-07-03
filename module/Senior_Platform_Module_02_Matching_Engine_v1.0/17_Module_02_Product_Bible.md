# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Module 02 Product Bible

## Executive Summary

Module 02 — Matching Engine is the core marketplace decision-support layer of the Generic Service Marketplace Framework Reference Implementation platform. It receives structured service needs from Module 01 and produces accepted, ranked, understandable provider options for the customer/family.

The module is designed for trust, explainability, operational control, future AI compatibility, and long-term scalability.

## Product Philosophy

The platform assists decision-making but does not take away the customer/family's final choice.

System behavior:

```text
Find eligible providers
Ask them to accept/reject
Show accepted options clearly
Rank transparently
Recommend explainably in future
Allow customer/family to choose
Hand off to Module 03
```

## Key Frozen Decisions

1. Matching is customer-choice based.
2. Requests may contain multiple service needs.
3. Matching is performed per service need.
4. Package options by independent provider or company are supported.
5. Eligibility, Matching, Fitness, Ranking, Presentation, and Recommendation are distinct concepts.
6. Company provider eligibility is hierarchical through company status.
7. Provider approval and complete profile are required before Matching.
8. Suspended providers are removed from Matching and public visibility.
9. Geographic service coverage is separate from residence.
10. Capacity is simplified in MVP as availability plus no conflict.
11. Distribution strategy is Broadcast in MVP, extensible later.
12. Provider responses are Accept/Reject in MVP.
13. Ranking is rule-based in MVP, AI-ready later.
14. Candidate cards and profiles are trust-focused.
15. Notifications are configurable by Platform Owner.
16. Matching expires based on configurable timings.
17. Manual intervention is permissioned and audited.
18. Module 02 ends at customer selection lock; Module 03 owns final reservation/contract/payment.

## Final Architecture

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
Recommendation Engine (future)
        ↓
Customer / Family Selection
        ↓
Module 03
```

## MVP Implementation Priorities

### Phase 1

- Provider lifecycle
- Service-level eligibility
- Basic geographic coverage
- Basic availability/conflict checking
- Broadcast distribution
- Accept/reject responses
- Accepted candidate list
- Summary cards
- Customer selection lock

### Phase 2

- Admin settings
- Ranking weight controls
- Notification configuration
- Expiration and reopen
- Manual intervention audit

### Phase 3

- Rich provider profiles
- Better trust metrics
- Company reliability score
- Recommendation explanations

### Future

- Wave-based distribution
- Smart distribution
- AI ranking
- AI recommendation
- Advanced capacity
- Multi-branch companies
- Map polygon coverage

## Development Notes

Do not implement Matching as a single giant function.

Recommended services:

- EligibilityService
- MatchingService
- DistributionService
- CandidateResponseService
- RankingService
- PresentationService
- NotificationService
- ExpirationService
- ManualInterventionService

## Quality Bar

A feature is not complete unless:

- It respects Module 01 boundaries.
- It is testable.
- It has explainable behavior.
- It handles failure states.
- It is permission-controlled if admin-facing.
- It creates audit logs when manually changed.

## Freeze Statement

Module 02 is now considered architecturally frozen. Future changes should be handled as explicit ADRs unless a major architectural conflict is discovered.
