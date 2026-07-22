# PRODUCT SPECIFICATION

## Project Vision

سالمندیار (Salmandyar — "Elder Companion") is a multi-tenant enterprise service marketplace platform connecting customers who need in-home senior care with independent caregivers and caregiving organizations.

The platform mediates the full lifecycle: discovery, request, offer, assignment, execution, payment, and review.

## Business Goals

- Enable customers to find and request qualified senior care services
- Enable independent caregivers and organizations to offer their services
- Mediate fair pricing, secure payment, and quality assurance
- Provide operational tools for platform administrators
- Support multi-tenant deployment for different markets/brands

## Target Users

### Customer

Individuals (typically family members) who need in-home care services for elderly relatives. They:

- Register via phone/OTP
- Create care-recipient profiles (elder profiles)
- Browse and search for caregivers/organizations
- Place service requests (orders)
- Manage payments, invoices, and disputes
- Submit reviews after service completion
- Save favorite providers

### Caregiver (Independent Provider)

Individual caregivers who provide senior care services independently. They:

- Register via phone/OTP
- Submit identity and professional documents for verification
- Build a professional profile (bio, skills, experience, gallery, availability)
- Receive and respond to service offers
- Manage their working schedule and capacity
- Track assignments, earnings, and reviews
- Optionally affiliate with a caregiving organization

### Company (Organization)

Caregiving organizations that employ or contract with caregivers. They:

- Register via phone/OTP (company admin)
- Submit company documents for verification
- Manage a staff roster of affiliated caregivers
- Assign their caregivers to eligible orders
- View financial summaries and reports
- Maintain a public company profile

### Administrator (Platform Staff)

Platform operators who maintain marketplace quality. They:

- Review and approve/reject identity documents
- Activate caregiver and organization profiles
- Monitor orders, disputes, and financial health
- Manage RBAC enforcement configuration
- View operational reports and system status

## Business Domains

### Marketplace

Public-facing discovery of caregivers and organizations. Includes directory search, filtering by city/service/availability, ranking, and detailed profile viewing.

### Orders

Customer-initiated service requests. An order specifies the service needed, the care recipient, schedule, and location. Orders flow through a 7-state lifecycle from request through completion.

### Offers

Supplier-initiated bids on orders. Caregivers (or their organizations) submit offers with pricing and terms. Offers flow through a 7-state lifecycle from submission through acceptance or withdrawal.

### Assignment

The binding of a specific supplier to an order. May result from matching (automated), manual operator selection, or offer acceptance. Assignments have their own confirmation lifecycle.

### Execution

Tracking of actual service delivery sessions. An execution session records when service begins, pauses, and completes.

### Invoices and Financial Documents

Commercial documents (invoices, credit notes) issued against orders. Documents flow through draft → issued → locked → paid states.

### Escrow

Held funds for pre-service payment. Escrow protects both parties: funds are held until service completion, then released (or refunded on dispute).

### Settlement

The process of moving held escrow funds to the provider's wallet after successful service delivery and objection-period expiry.

### Commission

Platform commission calculation and split between platform, organization, and caregiver. Governed by bilateral commission contracts.

### Reporting

Operational, financial, marketplace, and provider performance reports for administrators and providers.

### Notifications

Cross-channel (SMS, email, push, in-app) notification delivery for order updates, verification results, and system events.

### Search and Discovery

Supplier search with ranking based on reputation, availability, capacity, and service category. Used by both the public marketplace and internal matching engine.

### Identity Verification

Document-based verification of caregiver and organization identities. Required documents are tenant-configurable. Verification status gates marketplace visibility.

## Business Rules

- One active company affiliation per caregiver at a time
- Only ACTIVE + VERIFIED profiles are publicly visible
- One offer per supplier per order (database-enforced)
- Orders accept offers only while in NEW status
- Terminal states are immutable across all lifecycle entities
- Escrow amounts must satisfy conservation laws (held = released + refunded + remaining)
- Commission splits are frozen at order creation time (snapshot)
- The platform default language is Persian (fa-ir) with RTL layout

## High-Level Capabilities

| Domain | Status |
|---|---|
| User registration and authentication (phone/OTP) | Implemented (OTP generated but SMS delivery not wired) |
| Identity document verification workflow | Implemented |
| Profile activation lifecycle | Implemented |
| Public marketplace (directories, search, profiles) | Implemented |
| Order creation and lifecycle | Implemented |
| Offer submission lifecycle | Partially implemented (submit/edit/withdraw only) |
| Supplier matching and assignment | Implemented |
| Execution session tracking | Implemented |
| Financial documents and invoicing | Implemented |
| Escrow and pre-service payment | Implemented (fake PSP only) |
| Commission contracts and disputes | Implemented |
| Wallet and transaction ledger | Implemented |
| Customer portal | Implemented |
| Provider portal | Implemented |
| Organization portal | Implemented |
| Admin portal | Implemented |
| Reviews and reputation | Implemented |
| Notifications | Implemented (dispatch infrastructure; no real SMS/email provider) |
| Visual regression and accessibility testing | Implemented |
| Production deployment | Not implemented |

## Functional Scope

The platform covers:

- Multi-tenant identity and access management
- Document-based professional verification
- Public marketplace with caregiver and organization directories
- Full order-to-payment lifecycle
- Supplier matching, assignment, and execution tracking
- Financial engine (invoicing, escrow, settlement, wallets)
- Commission management with bilateral contracts
- Multi-portal web interface (customer, provider, organization, admin)
- REST API for programmatic access
- Background job processing
- Audit logging and event system

## Out of Scope

The following are explicitly not implemented and not planned for the current version:

- Mobile native applications
- Real-time messaging/chat between users
- Social features (posts, feeds, likes, follows, stories)
- Video/telehealth capabilities
- GPS/real-time location tracking
- AI-based caregiver matching or content moderation
- Multi-language support beyond Persian
- Third-party marketplace integrations

## Roadmap Vision

The implementation follows a phased approach:

1. Registration & Verification — COMPLETE
2. Caregiver Professional Profile — COMPLETE
3. Company Portal — COMPLETE
4. Customer Portal — COMPLETE
5. Marketplace Order Workflow (Offers) — IN PROGRESS (Sprint 5.1 delivered)
6. Invoice Workflow — NOT STARTED
7. Financial Engine Review — NOT STARTED
8. Payment & Settlement Review — NOT STARTED

Production readiness requires: real SMS provider, real payment gateway, and deployment infrastructure.
