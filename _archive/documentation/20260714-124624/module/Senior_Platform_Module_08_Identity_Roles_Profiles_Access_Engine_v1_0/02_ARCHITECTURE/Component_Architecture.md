# Module 08 Component Architecture

## Components

### 1. Identity Registry
Canonical store for identities, accounts, credentials, sessions and devices. It separates login mechanics from marketplace actor semantics.

### 2. Actor Registry
Maintains actor records, actor contexts, actor-type registry and actor lifecycle state. Other modules reference actors through stable actor IDs.

### 3. Access Decision Service
Policy decision point for authorization. It evaluates RBAC, tenant scope, ownership, membership, delegation, temporary grants, trusted-order grants, verification state, sanctions, and contextual obligations.

### 4. Role & Permission Service
Manages platform roles, tenant roles, custom roles, permission groups, hierarchy, and role assignment lifecycle.

### 5. Organization Administration Service
Manages organizations, departments, staff, operators, provider memberships, approval chains and organization ownership boundaries.

### 6. Provider Affiliation Service
Handles provider affiliation requests, company approval, rejection, revocation, suspension and conversion between independent and organization-affiliated provider contexts.

### 7. Profile Service
Manages public/private/sensitive profile segments, media, biographies, skills, experience, service areas, statistics, ratings references, verified badges and portfolio visibility.

### 8. Verification Service
Owns verification requests, required document sets, verification decisions, document review, lifecycle, expiry, renewal, rejection and badge issuance triggers.

### 9. Trusted Access Service
Creates order-scoped access grants for trusted persons. Grants are limited, time-bounded, revocable, auditable and resource-specific.

### 10. Session, Device & Token Service
Manages session creation, revocation, device trust, token issuance, token rotation, token scope, token expiry and suspicious device handling.

### 11. Impersonation & Emergency Access Service
Controls highly restricted admin impersonation and break-glass access. Requires explicit reason, approval policy, elevated audit and automatic revocation.

### 12. Audit & Event Publisher
Publishes CES events and stores security-grade audit trails for all meaningful identity/access changes and all sensitive access decisions.

## Architectural Boundary
Module 08 is both an identity domain and a policy decision provider. It is not a notification sender, financial authority, booking engine, execution engine or quality governance engine.

## Dependency Direction
Other modules depend on Module 08 for actor identity and permission decisions. Module 08 may consume events from Modules 01–07 but must not call their internal business services directly except through published contracts.

## Data Isolation
All tenant-bound data must contain `tenant_id` or an equivalent organization/marketplace scope. Cross-tenant visibility is denied unless an explicit platform-level permission exists.

## Extensibility
Actor types, verification types, badge types, profile field types and permission groups must be registry-driven, not hard-coded in application flow logic.
