# 35 — Customer Wallet Ledger Engine

## Purpose

Customer Wallet is a formal financial account, not a balance field.

Wallet balance is always derived from immutable wallet ledger entries.

```text
Wallet Balance = Sum(Wallet Ledger Entries)
```

## Supported Wallet Entry Types

```text
wallet_top_up_credit
order_payment_credit
order_payment_debit
refund_credit
cashback_credit
manual_credit
manual_debit
withdrawal_debit
adjustment_credit
adjustment_debit
hold
release_hold
expiration
```

## Case 1 — Direct Order Payment Through Wallet Ledger

Customer pays for a 1,000,000 order.

```text
Online Payment Successful: 1,000,000
Customer Wallet Credit: +1,000,000
Order Payment Debit: -1,000,000
Wallet Balance: 0
```

The wallet ledger shows the money path even if the customer never intentionally topped up the wallet.

## Case 2 — Wallet Top-up Then Partial Order Payment

Customer tops up wallet:

```text
Wallet Top-up: +7,000,000
Wallet Balance: 7,000,000
```

Later order amount is 10,000,000:

```text
Wallet Debit: -7,000,000
New Online Payment: +3,000,000
Order Fully Paid: 10,000,000
Wallet Balance: 0
```

## Case 3 — Refund to Wallet

Customer paid 10,000,000. Refund approved for 3,000,000.

```text
Refund Approved
→ Wallet Credit: +3,000,000
```

Refunds do not directly disappear into bank return unless an explicit withdrawal flow is created.

## Case 4 — Wallet Withdrawal

Customer requests money back to bank account.

```text
Wallet Withdrawal Requested
→ Platform Approval
→ Bank Transfer
→ Wallet Debit
→ Withdrawal Closed
```

## Case 5 — Cashback

Cashback is not Refund.

```text
Cashback Granted
→ Cashback Financial Document
→ Wallet Credit
```

Cashback must be separately reportable and configurable by policy.

## Wallet Holds

The wallet may support holds for future use:

```text
available_balance
held_balance
total_balance
```

A reserved order payment may first create a hold, then capture or release it.

## Audit Rule

Wallet entries are immutable. Errors are corrected only by adjustment entries.
