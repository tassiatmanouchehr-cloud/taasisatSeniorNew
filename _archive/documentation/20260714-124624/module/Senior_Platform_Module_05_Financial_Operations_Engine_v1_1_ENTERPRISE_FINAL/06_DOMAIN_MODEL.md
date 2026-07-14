# Generic Service Marketplace Framework

**Module 05 — Financial Operations, Ledger, Wallet & Settlement Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation (reference implementation of the Generic Service Marketplace Framework) |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine, Module 03 — Booking, Assignment & Service Activation Engine, Module 04 — Service Execution & Session Lifecycle Engine |
| **Next Modules** | Quality, Dispute, Reporting, Accounting/ERP Integration, Banking/PSP Adapters |
| **Language** | Persian business domain, English technical structure |

> Modules 01–04 are Frozen and Approved and are treated as baseline. Module 05 must not change their operational decisions unless a major architectural conflict is discovered.

> **Architecture Notice:** the project is a **Generic Service Marketplace Framework** with **Generic Service Marketplace Framework Reference Implementation** as the first reference implementation. Every section states the Core Platform pattern first, then its reference implementation mapping where useful.

# 06 — Domain Model

## Aggregates

### FinancialParty
Represents any party with financial identity: customer, provider, organization, platform, wallet, internal account or external counterparty.

### CommercialContract
Represents accepted offer and locked commercial amount.

### FinancialDocument
Represents any payable, refundable, adjustable or settlement document.

### PaymentTransaction
Represents proof of online payment, wallet debit, cash collection, manual collection or failed attempt.

### WalletAccount
Customer financial account whose balance is derived from wallet ledger entries.

### EscrowAccount
Liability account representing money held by platform for a contract/document until release/refund/allocation.

### LedgerEntry
Immutable debit/credit financial truth.

### Statement
Read model for stakeholder-facing financial history.

### SettlementBatch
Groups settlement items for operational execution.

### SettlementItem
Independent payable/receivable item with own state and retry history.

### FinancialPolicy
Configurable rule source resolved by Financial Policy Resolution Engine.

## Core Entities

- FinancialParty
- FinancialAccount
- CustomerWallet
- InternalAccount
- CommercialOffer
- CommercialContract
- FinancialDocument
- FinancialDocumentLine (future-ready)
- PaymentTransaction
- PaymentLink
- EscrowRecord
- MoneyOwnershipRecord
- CommissionRule
- CommissionCalculation
- PayableAllocation
- LedgerEntry
- LedgerJournal
- StatementRow
- WalletLedgerEntry
- RefundRequest
- AdjustmentDocument
- SettlementBatch
- SettlementItem
- SettlementAttempt
- FinancialEvent
- FinancialConfiguration

## Value Objects

- Money
- Currency
- Percentage
- CommissionBase
- PaymentWindow
- FinancialPeriod
- DocumentNumber
- ActorRole
- VisibilityLevel
- MoneyState
- CollectionModel
- PaymentMethod
- SettlementStatus

## reference implementation Mapping

| Core | Generic Service Marketplace Framework Reference Implementation |
|---|---|
| Customer Financial Party | Customer or Customer Delegate |
| Provider Financial Party | Independent Provider / Organization Provider |
| Organization Financial Party | Organization |
| Platform Financial Party | Platform Owner |
| Wallet Account | کیف پول Customer |
| Escrow Account | پول امانی نزد Platform Owner |
| Supplemental Invoice | فاکتور اضافه Provider |

---

## v1.1 Required Domain Entities

The following entities are mandatory additions before freeze:

```text
FinancialObligation
ObligationResolution
MoneyOwnershipRecord
FinancialParty
FinancialAccount
WalletLedgerEntry
ArchivedOffer
SupplementalInvoiceVersion
CashbackDocument
```

These entities are described in detail in files 32 through 40.
