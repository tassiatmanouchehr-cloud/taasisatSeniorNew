# Generic Service Marketplace Framework

**Module 03 — Booking, Assignment & Service Activation Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine |
| **Next Modules** | Module 04 — Service Execution / Care Delivery Engine, Module 05/06 — Payment & Settlement |
| **Language** | Persian business domain, English technical structure |

> Module 01 and Module 02 are Frozen and Approved and are treated as baseline. Module 03 must not change their decisions unless a major architectural conflict is discovered.

# 15 — Permission Matrix

## Roles

- Customer / Family
- Independent Provider
- Company Provider
- Company Admin/Dispatcher
- Support Operator
- Platform Owner
- System

## Permission Matrix

| Action | Customer | Independent Provider | Company Provider | Company | Support | Platform Owner |
|---|---:|---:|---:|---:|---:|---:|
| View own Service Case | Yes | No | No | No | Yes | Yes |
| View own pending commitment | No | Yes | Yes* | Yes | Yes | Yes |
| Accept/reject commitment | No | Yes | No (company decides) | Yes | No | No |
| Assign/substitute provider | No | No | No | Yes | No | Yes |
| Signal en route | No | Yes | Yes | N/A | No | No |
| Start service | No | Yes | Yes | N/A | No | No |
| Withdraw before start | Yes | No | No | No | Assist | Yes |
| Place manual hold | No | No | No | No | Permissioned | Yes |
| Release hold | No | No | No | No | Permissioned | Yes |
| Manually create/override Assignment | No | No | No | No | Permissioned | Yes |
| Extend Selection Lock | No | No | No | No | Permissioned | Yes |
| Change booking settings | No | No | No | No | No | Yes |
| View audit trail | No | No | No | No | Permissioned | Yes |
| View dashboards (own scope) | Yes | Yes | Yes | Yes | Yes | Yes |

\* Company provider's individual response ownership is company-controlled in MVP, consistent with Module 02's permission note.

## Security Principles

- Least privilege, consistent with Module 01/02.
- Transparent manual intervention, always audited (BR-326–330).
- Company-level commitment for company providers is enforced at the API layer, not just the UI.
- No hidden Assignment manipulation.
- One active Selection Lock per Service Need at a time (BR-304).
