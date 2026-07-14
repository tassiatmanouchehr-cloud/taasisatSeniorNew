# 33 — Money Ownership Lifecycle

## Purpose

The platform must explicitly distinguish between:

- Money paid by the customer
- Money held by the platform in escrow
- Money recognized as platform revenue
- Money payable to provider or organization
- Money actually settled to stakeholders

## Core Principle

Money held by the platform is not automatically platform revenue.

In the reference implementation reference implementation:

```text
Customer / Family pays
→ Money is held by Platform Owner in escrow
→ Service completes
→ Money becomes eligible for distribution
→ Policies split the amount
→ Settlement pays stakeholders
```

## Money State Machine

```text
customer_paid
held_in_platform_escrow
reserved_for_contract
eligible_for_distribution
policy_calculated
distributed_by_policy
pending_settlement
settled_to_stakeholders
refunded_to_wallet
closed
```

## Ownership States Explained

### customer_paid
A payment transaction was successful. The customer has transferred funds.

### held_in_platform_escrow
The platform controls the money operationally, but does not own it economically.

### reserved_for_contract
The money is linked to a specific accepted offer / contract.

### eligible_for_distribution
Module 04 has emitted a valid completion event and Module 05 may process the money.

### policy_calculated
Commission, payable allocation, settlement delay, and refund rules have been resolved.

### distributed_by_policy
Economic ownership has been assigned to Platform, Organization, Provider, Customer Wallet, or other Financial Parties.

### pending_settlement
The money is owed to a stakeholder but not yet paid out.

### settled_to_stakeholders
The payout was completed or otherwise resolved.

### refunded_to_wallet
The money was returned to Customer Wallet, not directly erased from the original transaction.

### closed
No further financial action remains except audit, reporting, or accounting export.

## Mandatory Rule

Every payment must have a Money Ownership Record.

```text
Payment Transaction
→ MoneyOwnershipRecord
→ Escrow / Wallet / Obligation / Ledger
```

## Forbidden Shortcut

The system must not treat `PaymentReceived` as `RevenueRecognized`.

Revenue recognition requires:

```text
Service completion
Financial eligibility
Policy application
Ledger posting
```
