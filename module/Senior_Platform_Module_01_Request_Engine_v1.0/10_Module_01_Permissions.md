# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Permissions

## Roles

- Customer / Family (request owner)
- Service Recipient
- Independent Provider
- Company Provider
- Company
- Support Operator
- Platform Owner
- System

## Permission Matrix

| Action | Family | Provider | Company | Support | Platform Owner |
|---|---:|---:|---:|---:|---:|
| Create / edit own request | Yes | No | No | Assist | Yes |
| Upload attachments | Yes | No | No | Assist | Yes |
| Confirm file type | Yes | No | No | No | Yes |
| Publish request | Yes | No | No | Assist | Yes |
| Delete request (pre-acceptance) | Yes | No | No | Permissioned | Yes |
| Remove single service need | Yes | No | No | Assist | Yes |
| View new eligible requests | No | Yes | Yes | Yes | Yes |
| Apply to request | No | Yes | Company-controlled | No | No |
| Withdraw application | No | Yes | Configurable | No | No |
| View full timeline | Own view | Own view | Own view | Permissioned | Yes |
| Cancel session | Yes | Rule-based | Rule-based | Permissioned | Yes |
| Change request settings | No | No | No | No | Yes |
| Review protection signals | No | No | No | Permissioned | Yes |
| View customer history | No | No | No | Permissioned | Yes |

## Security Principles

- Need-to-know exposure of every field, especially medical files.
- Role-filtered timeline: each role sees only its permitted entries.
- Guest can build a request but must identify before final submission.
- Deletion is free only before provider acceptance, and always recorded.
- Every manual override-like action is audited.
- Platform-first fairness: penalties and protections apply to all roles.
