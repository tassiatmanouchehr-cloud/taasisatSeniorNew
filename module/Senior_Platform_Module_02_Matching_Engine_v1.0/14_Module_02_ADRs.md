# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Architecture Decision Records

## ADR-02-01 — Customer-Choice Matching
System ranks and presents eligible accepted options; customer/family chooses.

## ADR-02-02 — Multi-Type Match Candidates
Candidates may be independent provider, company provider, company, individual package, company package, or mixed option.

## ADR-02-03 — Matching Per Service Need
Matching runs at `RequestServiceNeed` level.

## ADR-02-04 — Package Selection
Companies and independent providers may cover multiple needs if eligible.

## ADR-02-05 — Three-Layer Matching Architecture
Eligibility → Matching → Ranking, with Fitness and Presentation added.

## ADR-02-06 — Hierarchical Company Eligibility
Company eligibility is checked before company provider eligibility.

## ADR-02-07 — Explainable Eligibility
Eligibility results must include reasons.

## ADR-02-08 — Service-Level Eligibility
Service qualifications, price, documents, status, and experience are separate per service.

## ADR-02-09 — Identity & Verification
Platform approval and complete profile are required before Matching.

## ADR-02-10 — Suspension Policy
Suspended providers are removed from Matching and public visibility.

## ADR-02-11 — Provider Lifecycle
Standard lifecycle applies to providers.

## ADR-02-12 — Lifecycle Rules
APPROVED and ACTIVE are separate; temporary unavailability and reactivation are supported.

## ADR-02-13 — Geographic Coverage
Residence address and service coverage are separate; coverage supports city/area/radius.

## ADR-02-14 — Schedule & Availability
All major scheduling types are supported; providers have calendars and conflicts are checked.

## ADR-02-15 — Match Fitness
Eligibility and suitability are separate.

## ADR-02-16 — Simple Capacity
Capacity in MVP equals availability plus no conflict.

## ADR-02-17 — Broadcast Distribution
MVP broadcasts to all eligible providers; strategy architecture supports future modes.

## ADR-02-18 — Candidate Response Flow
Acceptance means willingness to be shown; not final commitment.

## ADR-02-19 — Accept/Reject Only
MVP provider response actions are Accept and Reject.

## ADR-02-20 — Candidate Presentation Cards
Summary cards must support fast trust-based comparison.

## ADR-02-21 — Recommendation Engine Reserved
Future explainable recommendation is reserved in architecture.

## ADR-02-22 — Rule-Based Ranking
MVP uses configurable rule-based ranking; AI later.

## ADR-02-23 — Provider Profile Trust Architecture
Profiles emphasize reviews, activities, price, verified trust badges, and topic-based experience.

## ADR-02-24 — Customer Selection Boundary
Module 02 records selection lock; Module 03 handles final reservation, contract, payment.

## ADR-02-25 — Notification Strategy
Push/SMS/Email/In-App are configurable by Platform Owner.

## ADR-02-26 — Expiration Strategy
Reminder and expiry are configurable; Platform Owner can reopen matching.

## ADR-02-27 — Manual Intervention
Manual actions are transparent, permissioned, and audited; final decision remains customer/family.
