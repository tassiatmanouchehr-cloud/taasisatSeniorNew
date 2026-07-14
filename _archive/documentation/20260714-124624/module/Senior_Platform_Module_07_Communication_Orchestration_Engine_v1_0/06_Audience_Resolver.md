# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
The Audience Resolver converts logical audiences in communication rules into concrete recipients.

## 2. Inputs
- CES event
- communication rule
- tenant context
- aggregate reference
- actor reference
- role mappings
- organization membership
- platform team mappings

## 3. Generic Audience Types
customer, provider, organization, organization_admin, platform_owner, platform_operator, support_agent, finance_operator, trust_operator, admin, external_contact, custom_role.

## 4. Resolution Examples
InvoicePaid:
- customer: aggregate customer owner
- provider: assigned provider for related service/order
- organization: provider organization or tenant organization
- platform_owner: configured platform owner team

AssignmentCreated:
- customer: requester/customer side
- provider: assigned provider
- organization_admin: provider organization admin when provider belongs to organization
- platform_operator: only if configured for operational visibility

## 5. Rules
- Never hard-code domain-specific names.
- Resolver must return recipient capability and contact availability.
- Resolver failures must be audited.
- Empty audience resolution must not fail the whole session unless audience is mandatory.
- Cross-tenant recipient leakage is forbidden.

## 6. Output
Resolved recipients include user_id, organization_id, external_contact_id, audience_type, locale, timezone, consent state and channel capabilities.
