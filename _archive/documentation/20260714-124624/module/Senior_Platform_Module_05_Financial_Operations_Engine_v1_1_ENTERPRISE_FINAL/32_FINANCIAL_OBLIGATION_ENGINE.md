# 32 — Financial Obligation Engine

## Purpose

Module 05 is not only a payment system. It is primarily a **Financial Obligation Management System**.

A payment is only one possible way to resolve an obligation. The system must first know:

- Who owes money?
- Who is owed money?
- Why does this obligation exist?
- Which document created it?
- When is it due?
- Has it been resolved, settled, offset, disputed, cancelled, or adjusted?

## Core Principle

Every financial document may create one or more obligations.

Examples:

```text
Completed Order
→ Platform owes Provider
→ Platform owes Organization
→ Platform earns Commission
```

```text
Cash Supplemental Invoice collected by Provider
→ Provider owes Platform commission
→ Provider owes Organization share, if applicable
```

```text
Refund approved
→ Platform / Wallet owes Customer
```

## Entity: FinancialObligation

Required fields:

```text
obligation_id
source_document_id
source_event_id
debtor_financial_party_id
creditor_financial_party_id
amount
currency
reason
obligation_type
due_at
status
priority
created_at
resolved_at
metadata
```

## Obligation Types

```text
customer_payment_due
platform_payable_to_provider
platform_payable_to_organization
provider_debt_to_platform
provider_debt_to_organization
organization_payable_to_provider
platform_commission_receivable
organization_commission_receivable
customer_wallet_credit_due
refund_due
cashback_due
manual_adjustment_due
settlement_due
```

## Obligation States

```text
created
eligible
pending_due_date
due
overdue
partially_resolved
resolved_by_payment
resolved_by_netting
resolved_by_adjustment
resolved_by_refund
resolved_by_wallet_credit
disputed
cancelled
reversed
closed
```

## Obligation Resolution Methods

```text
online_payment
cash_collection
wallet_debit
wallet_credit
bank_settlement
manual_payment
netting
offset
refund
adjustment
reversal
write_off
```

## Relationship to Ledger and Statement

Obligations are not a replacement for Ledger.

```text
Financial Document
→ Obligation Created
→ Obligation Resolved / Posted
→ Ledger Entries
→ Statement Projection
→ Settlement Batch
```

Obligation records explain *why* a party owes money. Ledger records prove *what was posted*. Statement records show *what users see*.

## Netting Rule

Before any settlement payment is created, the system must calculate the net position of each Financial Party by aggregating all open eligible obligations.

```text
Total credits owed to party
-
Total debts owed by party
=
Net settlement amount
```

If net amount is positive, the party may receive payment.
If zero or negative, no payout is created unless a manual override is authorized.
