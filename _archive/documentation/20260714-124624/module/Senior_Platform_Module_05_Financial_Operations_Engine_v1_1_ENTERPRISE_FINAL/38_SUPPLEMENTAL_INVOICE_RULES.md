# 38 — Supplemental Invoice Rules

## Purpose

Supplemental invoices are financial documents created after the contract price has been locked. They are commonly created near service closing, before provider and customer say goodbye.

## Core Rule

Only one active unpaid supplemental invoice may exist per service case unless policy explicitly allows otherwise.

```text
Only One Active Unpaid Supplemental Invoice Per Service Case
```

## Edit Window

The invoice issuer may edit a supplemental invoice for a configurable period.

Default reference implementation policy:

```text
30 minutes
```

This duration is configurable by Platform Owner.

## Lifecycle

```text
Supplemental Invoice Created
→ Edit Window Open
→ Invoice May Be Revised
→ Edit Window Closed
→ Invoice Locked
→ Payment Link Active
→ Online Payment OR Provider Collection Responsibility
→ Ledger Posted
→ Statement Updated
```

## Sequential Issuance Rule

A new supplemental invoice cannot be issued until the previous active supplemental invoice reaches a resolved state.

Resolved states include:

```text
paid_online
paid_cash_to_provider
provider_collection_responsibility_assigned
cancelled
reversed
adjusted
disputed_and_held
expired_by_policy
```

If still inside edit window, the issuer must revise the existing invoice instead of creating a new one.

## Online Payment Fallback

If online payment is not completed within configurable time, for example one hour:

```text
Collection Model changes to Provider Responsibility
Payment Method becomes Cash Assumed / Provider Collects
Provider must collect or confirm status
Commission debts are posted according to policy
```

The system should record responsibility, not falsely claim cash was physically received unless the provider confirms cash collection.

## AI Review Future Hook

Current version may send payment link directly after invoice creation.

Future version may insert:

```text
AI Financial Review
→ Approved / Flagged
→ Manual Review if needed
→ Payment Link Sent
```

AI review must be a pluggable review step, not hard-coded inside Invoice Engine.
