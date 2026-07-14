# 39 — Enterprise ADR Index M05-001 to M05-048

This file records the accepted architectural decisions for Module 05. Detailed documents may expand each ADR later, but every decision below is binding for Module 05 freeze.

| ADR | Decision | Status |
|---|---|---|
| M05-001 | Multi-Ledger Financial Architecture | Accepted |
| M05-002 | Reservation & Payment Expiration Engine | Accepted |
| M05-003 | Configurable Pre-Service Cancellation Financial Policy | Accepted |
| M05-004 | In-Service Cancellation & Partial Completion Financial Policy | Accepted |
| M05-005 | Supplemental Financial Documents | Accepted |
| M05-006 | Policy Application on All Financial Documents | Accepted |
| M05-007 | Complexity Behind Presets | Accepted |
| M05-008 | Configurable Commission for Supplemental Documents | Accepted |
| M05-009 | Supplemental Invoice at Closing Stage | Accepted |
| M05-010 | Multiple Payment Collection Models | Accepted |
| M05-011 | Issuer / Collector / Beneficiary Separation | Accepted |
| M05-012 | Financial Document Graph | Accepted |
| M05-013 | Simple User Flow, Controlled Financial Automation | Accepted |
| M05-014 | Financial Recognition Policy | Accepted |
| M05-015 | Operational Financial Statement Entries | Accepted |
| M05-016 | Stable Display Row with Immutable Source Events | Accepted |
| M05-017 | Balance-Based Settlement Rule | Accepted |
| M05-018 | Manual Settlement / Advance Payment Document | Accepted |
| M05-019 | Configurable Financial Period Engine | Accepted |
| M05-020 | Settlement Batch with Independent Settlement Items | Accepted |
| M05-021 | Automatic Retry Settlement Policy | Accepted |
| M05-022 | Financial Policy Resolution Core | Accepted |
| M05-023 | Contract Price Lock Architecture | Accepted |
| M05-024 | Commercial Pricing Decisions | Accepted |
| M05-025 | Commission Base / Provider Protection from Platform Discounts | Accepted |
| M05-026 | Archived Offers | Accepted |
| M05-027 | Discount Ownership Model | Accepted |
| M05-028 | Supplemental Invoice Edit Window & Sequential Issuance Rule | Accepted |
| M05-029 | Incorrect Contract Resolution | Accepted |
| M05-030 | Refund Destination to Customer Wallet | Accepted |
| M05-031 | Final Contract Amount with Future Line-Item Extensibility | Accepted |
| M05-032 | Draft Number Reservation | Accepted |
| M05-033 | Invoice Snapshot | Accepted |
| M05-034 | Invoice Lock After Payment | Accepted |
| M05-035 | Invoice Versioning | Accepted |
| M05-036 | Invoice Notes Instead of Attachments in Current Scope | Accepted |
| M05-037 | Digital Signature Future Readiness | Accepted |
| M05-038 | Refund Authorization by Platform Owner | Accepted |
| M05-039 | Financial Event Catalog | Accepted |
| M05-040 | Financial Event Visibility | Accepted |
| M05-041 | Financial Configuration Catalog | Accepted |
| M05-042 | Cross Module Contract Inbound | Accepted |
| M05-043 | Cross Module Contract Outbound Financial Outcomes | Accepted |
| M05-044 | Money Ownership Lifecycle | Accepted |
| M05-045 | Financial Obligation and Netting | Accepted |
| M05-046 | Multi-Party Financial Netting Engine | Accepted |
| M05-047 | Financial Party Architecture | Accepted |
| M05-048 | Customer Wallet Ledger Architecture | Accepted |

## Binding Principles

1. Contract price is immutable after payment.
2. Any financial correction must be represented by a new financial document.
3. Customer refunds first credit Customer Wallet.
4. Stakeholder statements are user-facing projections, not source of truth.
5. Ledger entries are immutable.
6. Obligations explain who owes whom.
7. Netting determines settlement eligibility.
8. Payment does not equal revenue.
9. Escrow is not platform revenue.
10. Financial policy resolution must be centralized.
11. Financial Party is the mandatory counterparty identity for Module 05.
12. Wallet balances are ledger-derived.
