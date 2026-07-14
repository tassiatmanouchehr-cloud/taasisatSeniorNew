# 34 — Financial Party Architecture

## Purpose

User, Provider, Organization, Collector, Issuer, and Beneficiary are operational roles. They are not always the same as the financial counterparty.

Module 05 therefore requires a separate concept:

# Financial Party

A Financial Party is any entity that can have:

- Balance
- Statement
- Ledger identity
- Wallet
- Receivable
- Payable
- Bank account
- Settlement account
- Tax identity
- Collection responsibility
- Payout eligibility

## Supported Party Types

```text
platform_owner
customer
independent_provider
organization
organization_provider
wallet_account
external_bank_account
system_clearing_account
refund_reserve
escrow_account
```

## Financial Party vs Operational Entity

```text
Operational Provider
→ may map to one Financial Party
→ may be paid through Organization Financial Party
→ may collect cash directly
```

```text
Organization
→ may receive all payouts
→ may split payouts to affiliated providers
→ may have multiple settlement accounts
```

## Required Relationships

```text
FinancialParty
├── FinancialAccount
├── WalletAccount
├── SettlementAccount
├── BankAccount
├── TaxProfile
├── RunningStatement
├── LedgerIdentity
├── PayoutPolicy
└── CollectionPolicy
```

## Role Separation

Each Financial Document must separately identify:

```text
issuer_financial_party
payer_financial_party
collector_financial_party
beneficiary_financial_parties
approver_party
settlement_payer_party
```

## Example

A company-affiliated provider creates a supplemental invoice and collects cash.

```text
Issuer: Provider
Collector: Provider
Beneficiaries: Platform, Organization, Provider
Payer: Customer
Settlement Payer: Platform or Organization depending on policy
```

The provider may owe the platform and organization their commission even though the cash never entered escrow.

## Design Rule

No Ledger Entry, Statement Entry, Wallet Entry, Settlement Item, or Obligation may point only to a user id. It must point to a Financial Party or Financial Account identity.
