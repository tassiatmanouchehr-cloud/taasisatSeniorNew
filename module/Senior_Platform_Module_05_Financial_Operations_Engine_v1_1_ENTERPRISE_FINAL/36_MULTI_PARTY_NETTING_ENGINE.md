# 36 — Multi-Party Financial Netting Engine

## Purpose

Settlement in a marketplace is not only between Platform and Provider. It may involve Customer, Platform, Organization, Organization Provider, Independent Provider, Wallet, and clearing accounts.

The Netting Engine converts many obligations into a final net position.

## Core Principle

No payout should be based only on completed orders.

Every payout must be based on the final eligible balance after applying:

```text
completed order credits
supplemental invoice credits
cash collection debts
platform commission
organization commission
manual payments
manual deductions
refunds
adjustments
previous failed settlements
wallet effects
```

## Example: Independent Provider Statement Logic

```text
Order credits:        +96,000,000
Cash invoice debt:    -20,000,000
Net balance:          +76,000,000
Settlement amount:     76,000,000
```

If a provider completed ten small orders but collected one very large cash invoice, the provider may become debtor to the platform. In that case no payout is created.

## Example: Company Provider Order + Cash Invoice

Policy:

```text
Contract amount: 10,000,000
Platform commission: 10%
Company commission from remaining: 10%
Supplemental invoice: 5,000,000
Supplemental invoice paid cash to provider
```

Contract distribution:

```text
Platform:      1,000,000
Organization:    900,000
Provider:      8,100,000
```

Cash supplemental invoice:

```text
Invoice amount: 5,000,000
Platform share:   500,000
Organization:     450,000
Provider keeps: 4,050,000
```

Since provider collected cash directly, provider owes:

```text
Platform + Organization = 950,000
```

Provider statement:

```text
Order credit:          +8,100,000
Cash invoice debt:       -950,000
Net provider balance:  +7,150,000
```

## Netting Algorithm

```text
1. Load eligible open obligations for a Financial Party group.
2. Normalize currencies and financial parties.
3. Separate credits and debts.
4. Apply policy priority and due-date rules.
5. Calculate net position per Financial Party.
6. Exclude zero or negative payout items unless manual override exists.
7. Create Settlement Items for positive net balances.
8. Keep negative balances open as receivables from party.
```

## Multi-Party Net Position

The engine must support graphs, not only pairs.

```text
Provider owes Platform
Provider owes Organization
Platform owes Provider
Platform owes Organization
Organization owes Provider
Wallet owes Customer
```

## Settlement Output

```text
NettingResult
├── party_id
├── net_amount
├── included_obligations
├── excluded_obligations
├── settlement_eligibility
├── warnings
└── generated_settlement_items
```

## Forbidden Shortcut

Do not create settlement based on `sum(completed_orders)` alone.
