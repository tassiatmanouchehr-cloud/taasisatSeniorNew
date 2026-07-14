# Generic Framework Correction Addendum v1.0

## Status
This module is corrected for the Generic Service Marketplace Framework. Domain-specific examples are allowed only inside reference-implementation mapping sections and must not define core architecture.

## Canonical Ownership Rules
- Identity, actor, role, profile, permission, session, device, organization membership and access decisions are owned by Module 08.
- Communications are owned by Module 07. Other modules publish CES events only; they must not send SMS, email, push, inbox, WhatsApp or webhook messages directly.
- Trust scoring, reviews, complaints, disputes, risk decisions and governance cases are owned by Module 06. Identity verification and access restriction execution are coordinated through Module 08.
- Financial ledgers, wallet, settlement, payment allocation and invoice lifecycle are owned by Module 05.
- Each module owns its state machines and emits canonical CES events using `module.entity.action` naming.

## Canonical Actor Vocabulary
Platform Owner, Platform Team Member, Organization, Organization Staff, Independent Provider, Organization Provider, Customer, Customer Delegate, Trusted Person, Public Guest, System Actor, External Integration.

## Canonical Event Naming
Events must use `module.entity.action`, for example `request.created`, `matching.candidate.generated`, `booking.assignment.created`, `execution.session.started`, `financial.payment.received`, `trust.case.opened`, `communication.message.sent`, `identity.role_assigned`.

## Canonical Configuration Naming
Configuration keys must use `module.group.setting`, for example `request.creation.requires_customer_identity`, `matching.ranking.max_candidates`, `booking.assignment.auto_accept_enabled`, `execution.presence.gps_required`, `financial.wallet.enabled`, `trust.review.enabled`, `communication.sms.enabled`, `identity.mfa.required_for_critical_actions`.

## Freeze Gate
This module can be frozen only when: domain leakage is removed from core, protected operations are delegated to Module 08, communication delivery is delegated to Module 07, events conform to CES, configuration keys conform to CCS, and cross-module contracts are explicit.
