# Module 08 Dependency Map

## Upstream Inputs
- CES: event envelope, event metadata, correlation IDs, causation IDs.
- CCS: configuration source for identity, verification, access, visibility and onboarding policies.
- Module 03: booking/assignment events used to create or revoke order-scoped access.
- Module 04: execution lifecycle events used to adjust trusted-person visibility and provider profile statistics.
- Module 05: financial access boundaries and payment-data masking requirements.
- Module 06: sanctions, trust score, disputes and badge governance inputs.
- Module 07: verified contact channels and communication preference dependencies.

## Downstream Consumers
- Module 01 uses actor/customer identity and access checks for request creation/visibility.
- Module 02 uses provider eligibility facts without owning identity verification logic.
- Module 03 uses provider/customer/company authorization and assignment permission decisions.
- Module 04 uses execution access decisions and trusted-person view permissions.
- Module 05 uses financial-data visibility and role-bound financial permissions.
- Module 06 uses identity, verification and profile records for reviews/disputes/governance.
- Module 07 uses contact permissions, actor channels and trusted-person communication eligibility.

## Forbidden Couplings
- No module may define its own actor types that bypass the Actor Registry.
- No module may expose private profile fields without Profile Service visibility decisions.
- No module may infer organization provider status from free-text company names.
- No module may grant trusted-person access without Trusted Access Service.
- No module may create platform/operator permissions outside Role & Permission Service.
