# Module 08 — Identity, Roles, Profiles & Access Engine v1.0

## 1. Mission
The Identity, Roles, Profiles & Access Engine provides the canonical enterprise identity and authorization layer for a generic, multi-tenant, event-driven service marketplace.

It owns:
- identity and account primitives;
- actor classification;
- authentication boundaries;
- authorization decisions;
- role and permission management;
- public/private profile structure;
- organization and staff hierarchy;
- provider affiliation lifecycle;
- customer and trusted-person access;
- verification and badge lifecycle;
- privacy and visibility decisions;
- identity/security audit events.

## 2. Non-Negotiable Constraints
1. Generic framework only; no vertical-specific vocabulary in core models.
2. Multi-tenant by design; every tenant-bound permission is tenant-scoped.
3. Event-driven; every meaningful state transition publishes CES-compliant events.
4. Configurable; every variable policy is externalized through CCS.
5. Auditable; access decisions, role changes, profile changes and verification decisions leave immutable audit trails.
6. Secure by default; deny-by-default authorization, least privilege, session hardening and token scoping.
7. Extensible; future actor types, verification types and access grant types must be addable without breaking existing contracts.
8. Zero business logic duplication; marketplace modules must not reimplement permission, visibility or actor classification logic.

## 3. Module Ownership
### Owned by Module 08
- User, Identity, Account, Credential, Session, Device.
- Actor and actor type registry.
- Platform owner/team actors.
- Organization/company actors.
- Staff/operator memberships.
- Independent provider and organization provider actors.
- Customer actor.
- Trusted person order-scoped actor.
- Role, permission, permission group, delegated permission, temporary permission.
- Tenant-aware access evaluation.
- Public/private/sensitive profile fields.
- Provider/company/platform profiles.
- Verification requests, documents, decisions, badges.
- Identity lifecycle and onboarding state.
- Impersonation and emergency access grants.

### Not Owned by Module 08
- Request contents: Module 01.
- Matching/ranking logic: Module 02.
- Booking/assignment lifecycle: Module 03.
- Service execution status: Module 04.
- Wallet, ledger, payout, invoice/payment settlement: Module 05.
- Reviews, disputes, sanctions, appeals and quality governance: Module 06.
- Notification channel delivery: Module 07.

Module 08 may expose identity/access facts to these modules, and may consume their events to adjust access grants, but it does not own their domain state.

## 4. Canonical Actor Types
- `PLATFORM_OWNER`: ultimate marketplace owner actor.
- `PLATFORM_TEAM_MEMBER`: staff member operating marketplace-level functions.
- `ORGANIZATION`: tenant/provider company actor.
- `ORGANIZATION_STAFF`: operator/admin/staff member of an organization.
- `INDEPENDENT_PROVIDER`: provider operating outside organization affiliation.
- `ORGANIZATION_PROVIDER`: provider affiliated with one or more organizations through approved membership.
- `CUSTOMER`: customer account initiating or managing service demand.
- `TRUSTED_PERSON`: limited, order-scoped actor invited by a customer.
- `SYSTEM_ACTOR`: internal automation actor used only for audited system actions.
- `FUTURE_ACTOR_TYPE`: reserved extension mechanism; never hard-code exhaustive actor assumptions.

## 5. Identity vs Actor vs Profile
- `Identity`: verified or partially verified real-world subject or organization identity.
- `Account`: login-capable container bound to one identity or controlled organization subject.
- `User`: human login principal.
- `Actor`: authorization subject used by marketplace engines.
- `Profile`: public/private marketplace representation of an actor.
- `Role`: named bundle of permissions under a scope.
- `Permission`: atomic capability checked by the Access Engine.

A single human user may have multiple actor contexts, for example organization staff in one tenant and customer in another. Access decisions must therefore always include actor context and scope.

## 6. Access Decision Contract
Every protected operation in the marketplace must ask:

```text
Can actor A perform action P on resource R within scope S under context C?
```

The engine returns:
- allow/deny;
- evaluated actor context;
- matched role/permission/delegation;
- policy reason code;
- obligations such as MFA, re-authentication, masking, approval, or audit escalation.

## 7. Primary Capabilities
1. Registration and onboarding for company, independent provider and customer.
2. Company-affiliated provider affiliation request and approval.
3. Staff invitation, role assignment and permission boundaries.
4. Custom roles and tenant-specific permission groups.
5. Delegated and temporary permissions.
6. Trusted-person order-scoped access.
7. Profile publication and visibility control.
8. Verification workflow for identity, professional credentials, organization and documents.
9. Badge issuance and lifecycle.
10. Session, device and access-token management.
11. Impersonation and emergency access with strong controls.
12. Complete event and configuration integration.

## 8. Final Invariant
No actor should gain access merely because they exist. Access is granted only through explicit role, membership, delegation, order-scoped grant, system policy, or audited emergency break-glass flow.
