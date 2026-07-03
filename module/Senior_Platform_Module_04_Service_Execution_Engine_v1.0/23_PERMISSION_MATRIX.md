# Generic Service Marketplace Framework

**Module 04 — Service Execution & Session Lifecycle Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation (reference implementation of the Generic Service Marketplace Framework) |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine, Module 03 — Booking, Assignment & Service Activation Engine |
| **Next Modules** | Module 05/06 — Payment & Settlement, future Quality / Dispute / Reporting modules |
| **Language** | Persian business domain, English technical structure |

> Modules 01–03 are Frozen and Approved and are treated as baseline. Module 04 must not change their decisions unless a major architectural conflict is discovered.

> **Architecture Upgrade Notice:** starting with this module, the project is no longer designed as a single-purpose reference implementation platform. It is designed as a **Generic Service Marketplace Framework** (Layer 1 — Core Platform, domain-independent) with **Generic Service Marketplace Framework Reference Implementation as its first reference implementation** (Layer 2 — reference implementation Domain Mapping). Every section below states the Core Platform pattern first, then its reference implementation mapping.

# 23 — Permission Matrix

## Roles

- Customer
- Provider
- Organization
- Platform Team
- System

## Permission Matrix

| Action | Customer | Provider | Organization | Platform Team |
|---|---:|---:|---:|---:|
| Declare en route / arrival | No | Yes | No | No |
| Submit start checklist | No | Yes | No | No |
| Start session | No | Yes | No | No |
| Record activity / observation / evidence | No | Yes | No | No |
| Pause / resume session | No | Yes | Permissioned | Permissioned |
| Report issue (create Exception) | Yes | Yes | Yes | Yes |
| Request extension | Yes | Yes | No | No |
| Approve/reject extension (counterpart) | Yes | Yes | No | No |
| Resolve extension via Operational Review | No | No | Yes | Yes |
| Mark session completed (provider side) | No | Yes | No | No |
| Confirm completion (customer side) | Yes | No | No | No |
| Dispute completion | Yes | No | No | No |
| Resolve completion dispute | No | No | Yes | Yes |
| Add Review / Correction / Note to a record | No | No | Yes | Yes |
| Override location validation | No | No | Yes (audited) | Yes (audited) |
| Assign / resolve Exception | No | No | Yes | Yes |
| Change execution settings | No | No | No | Yes |
| View full audit trail | No | No | Permissioned | Yes |
| View own session dashboard | Yes | Yes | Yes | Yes |

## Security Principles (from Platform Architectural Principles)

- Least privilege by default (Principle 19).
- No one — including Organization or Platform Team — may edit or delete an execution record once created; only append reviews, corrections, or notes (ADR-04-001).
- Manual overrides always require reason, actor, role, timestamp, and audit trail (BR-04-020).
- Internal notes never default to Customer-visible (BR-04-044).
- Real phone numbers are never exposed between Customer and Provider (ADR-04-008).
