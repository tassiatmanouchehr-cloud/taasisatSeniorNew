# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


## 1. Purpose

Module 02 finds, evaluates, ranks, presents, and allows selection of suitable service providers for a customer/family request.

The module supports a healthcare/home-care marketplace where the customer or the customer family chooses from providers who are eligible and have accepted the request.

## 2. Core Product Principle

The platform does not force a provider on the customer/family. It supports decision-making through transparent eligibility, ranking, presentation, and recommendation.

**Final choice remains with the customer or family.**

## 3. Terminology

| Term | Meaning |
|---|---|
| Customer or Customer Delegate | Customer-side actor who requests and selects services |
| Independent Provider | Independent provider/provider/provider |
| Organization Provider | Provider/provider affiliated with a company |
| Organization | Provider organization that can offer services or affiliated providers |
| Platform Owner | Platform owner / highest-level business administrator |
| Service Need | One specific service requirement inside a request |
| Candidate | A provider option produced by matching |
| Matching | Generating valid provider options |
| Ranking | Ordering accepted candidates for display |
| Fitness | How suitable an eligible candidate is for a specific need/request |

## 4. Actors

- Customer / Family
- Independent Provider
- Company Provider
- Company
- Platform Owner
- Platform Support / Operator
- System / Matching Engine
- Future AI Engine

## 5. Scope

Module 02 includes:

- Eligibility Engine
- Matching Engine
- Fitness Evaluation
- Ranking Engine
- Distribution Strategy
- Candidate Response Flow
- Candidate Presentation Layer
- Recommendation Engine reservation in architecture
- Provider Profile trust structure
- Notification strategy
- Expiration strategy
- Manual intervention strategy
- Customer selection boundary

## 6. Out of Scope

- Request creation and validation
- Payment
- Contract signing
- Final legal commitment
- Final reservation confirmation
- Invoicing
- Medical diagnosis
- Provider payroll

## 7. High-Level Requirements

### FR-201 — Service-Need-Based Matching
Matching must run at `RequestServiceNeed` level, not only at full request level.

### FR-202 — Multi-Need Matching
A single request may include multiple service needs, such as bathing/care, injections, and physiotherapy.

### FR-203 — Mixed Candidate Types
The system must support:

- Independent Provider
- Organization Provider
- Organization
- package option by individual
- package option by company

### FR-204 — Candidate Acceptance Before Customer Display
Only candidates who accept the request are shown to the customer/family.

### FR-205 — Customer Selection
The customer/family selects the final option from accepted candidates.

### FR-206 — Manual Intervention
Platform Owner/support can intervene when matching fails or needs operational support.

## 8. Non-Functional Requirements

- Explainability
- Auditability
- Performance through precomputed eligibility where possible
- Configurability by Platform Owner
- Security and permission separation
- Future AI compatibility
- Avoid hidden manipulation of ranking

## 9. MVP Philosophy

Version 1 must be reliable and understandable. It must avoid premature complexity while preserving architectural extension points for wave distribution, smart distribution, AI ranking, richer capacity, and recommendation.
