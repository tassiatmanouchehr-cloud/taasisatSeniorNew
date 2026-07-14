# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Traceability Matrix

| Decision / Rule | Product Spec | Business Rules | Architecture | Data Model | API | UI | Tests |
|---|---|---|---|---|---|---|---|
| Step-by-step creation | FR-101 | BR-101 | Request Start | requests | draft/patch | step form | TS-101 |
| Guest start, late identity | FR-102 | BR-102/103 | Request Start | requests.owner | identify API | final step | TS-102 |
| Form + rich attachments | FR-103 | BR-105/106/107 | Collection | request_attachments | attachments API | request form | TS-107/108 |
| AI file classify + confirm | FR-104 | BR-108/109 | Collection | attachments.suggested/confirmed | confirm-type API | file confirm screen | TS-110/112 |
| Multi-service-need | FR-105 | BR-110/111 | Matching-ready | request_service_needs | needs API | request form | TS-113 |
| Validate before publish | FR-106 | BR-112/113 | Validation | request_validations | publish API | publish flow | TS-116 |
| Targeted publishing | FR-107 | BR-114/115 | Publishing | request_publications | publish API | new-requests screen | TS-119/120 |
| Provider new-request count | FR-107 | BR-116 | Publishing | applications | provider requests API | new requests screen | TS-121 |
| Behaviour signals | NFR | BR-117 | Publishing | request_events | internal | none | TS-122 |
| Request life cycle | FR-108 | BR-118 | Workflow | requests.status | status APIs | status/timeline | TS-123 |
| Controlled editing | FR-109 | BR-119/120/121 | Workflow | requests | patch API | edit screen | TS-126/127 |
| Single-need removal | FR-105 | BR-122 | Workflow | request_service_needs | remove-need API | edit screen | TS-115 |
| Free deletion pre-accept | FR-112 | BR-123/124/125 | Workflow | customer_request_history | delete API | history screen | TS-129/130 |
| No-selection timeout | FR-108 | BR-126/127/128 | Workflow | request_settings | settings API | status screen | TS-132/134 |
| Selected-provider follow-up | FR-108 | BR-129/130 | Follow-Up | request_timeline_entries | timeline API | status screen | TS-135/136 |
| Recurring as contract | FR-111 | BR-131/132/133 | Contract | contracts / sessions | contract APIs | sessions screen | TS-137/139 |
| Cancellation + penalties | FR-112 | BR-134-138 | Workflow | applications / contracts | cancel APIs | edit/sessions | TS-140/142 |
| Platform protection | FR-113 | BR-139/140/141 | Protection | protection_signals | protection APIs | signals panel | TS-143/147 |
| Event-driven | NFR | BR-144 | Event Layer | request_events | EventBus | none | TS-150 |
| Role-filtered timeline | FR-110 | BR-142/143 | Timeline | request_timeline_entries | timeline API | timeline screen | TS-148/149 |
| Need-to-know (Principle 1) | Core Principle | BR-114 | Principle 1 | visibility_scope | internal | role views | TS-149 |
| Platform first (Principle 2) | Core Principle | BR-138 | Principle 2 | penalties | internal | policy UI | TS-141/142 |
| Module boundary | Scope | BR-145/146 | Boundary | requests.status | publish API | handoff | TS-154 |
