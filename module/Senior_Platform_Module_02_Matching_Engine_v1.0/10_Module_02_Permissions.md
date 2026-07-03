# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# Permissions

## Roles

- Customer / Family
- Independent Provider
- Company Provider
- Company Admin
- Support Operator
- Platform Owner
- System

## Permission Matrix

| Action | Customer | Independent Provider | Company Provider | Company | Support | Platform Owner |
|---|---:|---:|---:|---:|---:|---:|
| View accepted candidates | Yes | No | No | No | Yes | Yes |
| View own invitation | No | Yes | Yes* | Yes | Yes | Yes |
| Accept/Reject invitation | No | Yes | Configurable | Company-controlled in MVP | No | No |
| Withdraw acceptance | No | Yes | Configurable | Yes | No | No |
| Select candidate | Yes | No | No | No | No | Special only |
| Reopen matching | No | No | No | No | Permissioned | Yes |
| Restart matching | No | No | No | No | Permissioned | Yes |
| Rerank | No | No | No | No | Permissioned | Yes |
| Suggest candidate | No | No | No | No | Permissioned | Yes |
| Change ranking weights | No | No | No | No | No | Yes |
| Change notification settings | No | No | No | No | No | Yes |
| View audit logs | No | No | No | No | Permissioned | Yes |

\* Company provider response ownership may evolve. MVP should avoid ambiguity by making company-related acceptance operationally controlled by the company when company responsibility is involved.

## Security Principles

- Least privilege
- Transparent intervention
- No hidden ranking manipulation
- Suspended providers hidden from public views
- One active customer selection per service need
- Audit logs for all manual override-like behavior
