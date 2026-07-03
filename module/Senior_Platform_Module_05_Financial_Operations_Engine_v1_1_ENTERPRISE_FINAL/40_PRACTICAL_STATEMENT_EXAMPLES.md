# 40 — Practical Running Statement Examples

## Purpose

These examples preserve the intended user-facing financial experience. The statement must feel like a bank statement: simple, readable, and balance-oriented.

## Example 1 — Independent Provider with Platform Commission 20%

| Row | Date | Document | Description | Gross Amount | Debit | Credit | Balance | Diagnosis |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | — | Order 1253 | Completed service | 10,000,000 | — | 8,000,000 | 8,000,000 | Creditor |
| 2 | — | Order 1254 | Completed service | 8,000,000 | — | 6,400,000 | 14,400,000 | Creditor |
| 3 | — | Order 1255 | Completed service | 12,000,000 | — | 9,600,000 | 24,000,000 | Creditor |
| 4 | — | Invoice 1546 | Cash collected by provider | 7,000,000 | 1,400,000 | — | 22,600,000 | Creditor |
| 5 | — | Settlement | Bank transfer to provider | — | 22,600,000 | — | 0 | Closed |

## Example 2 — Completed Orders and Large Cash Invoice

Provider has order credits but collected a large cash invoice.

| Row | Document | Gross Amount | Debit | Credit | Balance | Diagnosis |
|---:|---|---:|---:|---:|---:|---|
| 1 | Order 1257 | 6,000,000 | — | 4,800,000 | 4,800,000 | Creditor |
| 2 | Invoice 1549 Cash | 50,000,000 | 10,000,000 | — | -5,200,000 | Debtor |
| 3 | Order 1268 | 6,000,000 | — | 4,800,000 | -400,000 | Debtor |
| 4 | Invoice 1589 Online | 50,000,000 | — | 40,000,000 | 39,600,000 | Creditor |

Rule: settlement is based on final balance, not on completed orders alone.

## Example 3 — Incomplete Order Display Row

| Row | Document | Description | Gross Amount | Debit | Credit | Balance | Diagnosis |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Order 1393 | Not completed yet | 60,000,000 | — | — | 10,400,000 | Creditor |

When the order completes, the same stable display row may update visually:

| Row | Document | Description | Gross Amount | Debit | Credit | Balance | Diagnosis |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Order 1393 | Completed | 60,000,000 | — | 48,000,000 | 58,400,000 | Creditor |

Behind the scenes, immutable source events remain separate:

```text
StatementInformationalEntryCreated
FinancialRecognitionPosted
```

## Example 4 — Company Provider, Online Supplemental Invoice

Policy:

```text
Contract: 10,000,000
Platform commission: 10%
Organization commission: 10% of remaining amount
Supplemental invoice: 5,000,000
Supplemental invoice paid online
```

Contract allocation:

```text
Platform:      1,000,000
Organization:    900,000
Provider:      8,100,000
```

Supplemental allocation:

```text
Platform:        500,000
Organization:    450,000
Provider:      4,050,000
```

Provider statement:

| Document | Debit | Credit | Balance |
|---|---:|---:|---:|
| Order 1253 | — | 8,100,000 | 8,100,000 |
| Invoice 1548 Online | — | 4,050,000 | 12,150,000 |

Organization statement:

| Document | Debit | Credit | Balance |
|---|---:|---:|---:|
| Order 1253 | — | 900,000 | 900,000 |
| Invoice 1548 Online | — | 450,000 | 1,350,000 |

Platform statement:

| Document | Debit | Credit | Balance |
|---|---:|---:|---:|
| Order 1253 | — | 1,000,000 | 1,000,000 |
| Invoice 1548 Online | — | 500,000 | 1,500,000 |

## Example 5 — Company Provider, Cash Supplemental Invoice

Same 5,000,000 supplemental invoice, but customer pays cash to provider.

Provider collected total cash, so provider owes shares to platform and organization.

```text
Platform share: 500,000
Organization share: 450,000
Provider debt: 950,000
```

Provider statement:

| Document | Debit | Credit | Balance |
|---|---:|---:|---:|
| Order 1253 | — | 8,100,000 | 8,100,000 |
| Invoice 1548 Cash | 950,000 | — | 7,150,000 |

This is the practical expression of Multi-Party Netting.
