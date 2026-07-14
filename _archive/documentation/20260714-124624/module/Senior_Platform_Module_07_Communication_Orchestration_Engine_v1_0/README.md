# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## Package Purpose

This package defines Module 07 of the Generic Service Marketplace Framework: the Communication Orchestration Engine.

The module is the centralized communication brain of the marketplace. It receives CES Events from all business modules and decides:

- who must be informed,
- through which channels,
- using which templates,
- under which tenant, role, preference, legal and criticality rules,
- with what retry, fallback, escalation and audit behavior.

## Core Principle

Business modules publish events. They do not send messages.

Module 07 converts events into governed communications across SMS, email, push, in-app notifications, inbox, dashboard notifications, chat, announcements, reminders, campaigns, broadcasts, webhooks, and optional voice calls.

## Required Reading Order

1. 01_Master_Architecture.md
2. 02_Domain_Model.md
3. 03_Communication_Rule_Model.md
4. 04_Event_Catalog.md
5. 05_Configuration_Catalog.md
6. 20_Cross_Module_Contracts.md
7. 28_Module_Freeze_Report.md

## File Index

| File | Purpose |
|---|---|
| 01_Master_Architecture.md | High-level architecture and rules |
| 02_Domain_Model.md | Aggregates, entities, value objects and invariants |
| 03_Communication_Rule_Model.md | Event-to-message rule system |
| 04_Event_Catalog.md | CES events consumed and emitted by Module 07 |
| 05_Configuration_Catalog.md | CCS configuration keys |
| 06_Audience_Resolver.md | Generic recipient resolution |
| 07_Channel_Resolver.md | Channel selection and activation |
| 08_Template_Engine.md | Template rendering, versioning and validation |
| 09_Provider_Abstraction.md | SMS/email/push/voice/provider adapters |
| 10_Delivery_Tracking.md | Delivery jobs, attempts and statuses |
| 11_Inbox_Engine.md | In-app inbox and persistent notification surface |
| 12_Conversation_Engine.md | Chat and conversation model |
| 13_Reminder_Engine.md | Scheduled and repeated communications |
| 14_Announcement_System.md | Tenant/platform announcements |
| 15_Campaign_Engine.md | Broadcast and campaign messaging |
| 16_User_Preferences.md | Consent, opt-in/out and preference hierarchy |
| 17_Retry_Fallback_Escalation.md | Failure recovery and escalation |
| 18_Audit_Timeline.md | Evidence, communication timeline and support visibility |
| 19_Security_Privacy.md | Security, privacy and compliance requirements |
| 20_Cross_Module_Contracts.md | Contracts with Modules 01–06 and future modules |
| 21_Dependency_Map.md | Dependencies and boundaries |
| 22_Event_Flow_Diagrams.md | Text diagrams for main event flows |
| 23_State_Machines.md | State models |
| 24_Entity_Relationships.md | Entity relationships |
| 25_Extensibility_Guide.md | Adding new channels/providers/features |
| 26_Architecture_Principles.md | Non-negotiable design principles |
| 27_Enterprise_Checklist.md | Review checklist |
| 28_Module_Freeze_Report.md | Freeze readiness report |

## Domain Genericity

The framework core uses generic actors only:

- customer
- provider
- organization
- platform_owner
- platform_operator
- support_agent
- finance_operator
- trust_operator
- admin
- external_contact

Domain-specific terms such as customer, provider, provider, doctor, technician, driver or salon worker belong only to reference implementation mapping layers.


---

# Generic Framework Correction Notice
This package has been corrected to operate as a generic, reusable, event-driven service marketplace module. Domain-specific terminology, where retained, is non-normative reference implementation material only.
