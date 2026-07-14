# Cross-Module Contracts

## Module 01 Request Engine
Requires:
- customer actor validation;
- trusted-person access decisions for request/order visibility;
- private contact masking.

Module 08 Provides:
- `actor.customer.can_create_request` decision;
- customer identity/profile references;
- trusted-access grant facts.

## Module 02 Matching Engine
Requires:
- provider eligibility;
- provider verification status;
- provider organization context;
- public profile facts.

Module 08 Provides:
- provider actor context;
- affiliation status;
- verification badges;
- profile visibility-safe public data.

## Module 03 Booking & Assignment
Requires:
- assignment authority;
- provider context validation;
- organization staff permissions;
- customer/trusted-person order access.

Module 08 Provides:
- access decisions for assignment, reassignment and order management;
- order-scoped trusted access creation interface.

## Module 04 Service Execution
Requires:
- execution view/update permissions;
- provider/customer/staff actor boundaries;
- trusted-person progress view.

Module 08 Provides:
- service execution access decisions;
- trusted order visibility policy.

## Module 05 Financial Operations
Requires:
- financial permissions;
- masking rules;
- financial document access authorization.

Module 08 Provides:
- role-bound financial access decisions;
- sensitive data access audit.

## Module 06 Trust & Governance
Requires:
- identity and profile facts;
- verification state;
- sanctions integration.

Module 08 Provides:
- identity/actor/profile references;
- consumes governance sanctions as access constraints.

## Module 07 Communication
Requires:
- verified communication channels;
- actor communication eligibility;
- trusted-person notification grants.

Module 08 Provides:
- actor contact visibility and communication consent/access facts;
- trusted-person communication permission.
