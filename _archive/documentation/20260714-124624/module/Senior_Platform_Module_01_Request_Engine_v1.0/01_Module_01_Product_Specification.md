# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Product Specification

## 1. Purpose

Module 01 lets a customer or family describe a care need, attach supporting information, and submit it as a structured request that the platform can validate, create, and publish to the right providers at the right time.

The module is the entry point of the whole marketplace. Everything downstream (matching, selection, contract, payment) consumes what Module 01 produces.

## 2. Core Product Principle

The platform must not show information to everyone. **The platform must show the right information, to the right people, at the right time, and only as much as necessary.**

This principle governs request publishing, notifications, medical files, and timelines across the entire product.

## 3. Terminology

| Term | Meaning |
|---|---|
| Customer or Customer Delegate | Customer-side actor who creates and owns the request |
| گیرنده‌ی خدمت | The service recipient (the service recipient person or customer) the request is for |
| ارائه‌دهنده | Provider: independent provider, company provider, or company |
| درخواست (Request) | A single service request created by a family/customer |
| Service Need | One specific service inside a request (e.g. night nursing, physiotherapy, home lab) |
| قرارداد (Contract) | A recurring commitment that contains multiple sessions |
| جلسه (Session) | One occurrence inside a contract |
| اعلام آمادگی (Application) | A provider signalling willingness for a published request |
| Timeline | Role-filtered chronological history of a request |
| Platform Owner | Platform owner / highest-level business administrator |

## 4. Actors

- Customer / Family (request owner)
- Service Recipient
- Independent Provider
- Company Provider
- Company
- Platform Support / Operator
- Platform Owner
- System / Request Engine
- AI File Classifier (assistive)

## 5. Scope

Module 01 includes:

- Request Start (entry into the flow)
- Information Collection (form, text, photo, video)
- AI-assisted file classification with human confirmation
- Validation
- Request Creation
- Request Publishing (targeted distribution)
- Multi-service-need requests
- Request status / life cycle
- Request editing after creation
- Request-level cancellation and deletion rules
- Request/Contract split for recurring services
- Session-level cancellation
- Request Timeline (role-based)
- Event stream (event-driven foundation)
- Platform-protection triggers created at request time

## 6. Out of Scope

- Provider eligibility evaluation, fitness, ranking (Module 02)
- Candidate presentation and customer selection UI logic (Module 02)
- Provider profiles and trust scorecard details (Provider / Trust Engine)
- Payment, invoicing, commission settlement (Payment Engine)
- Final legal contract enforcement and dispute resolution
- Medical diagnosis
- GPS live tracking (planned for a later phase)

## 7. High-Level Requirements

### FR-101 — Step-by-Step Request Creation
The request must be created through a guided, step-by-step flow, not a single dense form.

### FR-102 — Guest Start, Late Identification
A user may build a request as a guest and only complete mobile number, verification code, and personal identity at the final step.

### FR-103 — Form-First with Rich Attachments
The main experience is a traditional structured form, but the user must also be able to add free-text detail, photos, and video. Attachments must be compressed and size-limited.

### FR-104 — AI-Assisted File Classification
When a user uploads a file, the system may guess its type and ask a single confirmation question ("This looks like a doctor's prescription — is that correct? ✅ Yes / ✏️ Correct it"). The user, not the AI, owns the final classification.

### FR-105 — Multi-Service-Need Request
A single request may contain several service needs (e.g. night provider + physiotherapy + home lab test).

### FR-106 — Validation Before Publish
A request must pass validation (sufficient information present) before it can be published.

### FR-107 — Targeted Publishing
A published request must be shown only to eligible providers, filtered by service, city/coverage, availability, and completeness — never blindly to everyone.

### FR-108 — Request Life Cycle
Every request must follow a defined status machine from Draft to Completed / Cancelled.

### FR-109 — Editable Request with Controlled Re-Publish
The owner may edit a request after creation; the system must apply defined re-publish / re-confirm rules depending on the current status.

### FR-110 — Request Timeline
Each request must keep a chronological timeline, shown to each role only for the parts that role is allowed to see.

### FR-111 — Recurring as Contract
A recurring need (e.g. daily at 8am for 30 days) must be modelled as a Contract containing sessions, not as a single order and not as N independent orders.

### FR-112 — Request-Level Cancellation Rules
The engine must enforce who can cancel or delete a request, and until when.

### FR-113 — Platform Protection at Request Time
The engine must detect and discourage attempts to move the deal off-platform from the moment a request exists.

## 8. Non-Functional Requirements

- Event-driven core so downstream modules can react without coupling
- Explainable validation and publishing decisions
- Auditability of every request state change
- Configurability by Platform Owner (timeouts, reminders, publishing breadth)
- Privacy by default for medical files (need-to-know exposure)
- High throughput (designed for 100k+ requests/day)
- Future compatibility with GPS, smart distribution, and AI ranking

## 9. MVP Philosophy

Version 1 must be simple for families and reliable at scale. It should avoid premature complexity (no live GPS, no AI ranking yet) while freezing the request life cycle, the request/contract split, the event model, and the protection triggers, because these are expensive to change later.
