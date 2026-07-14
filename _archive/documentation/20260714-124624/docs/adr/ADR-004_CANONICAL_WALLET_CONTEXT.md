# ADR-004 — `apps.wallet` as the Canonical Wallet Bounded Context

## Status

Accepted — Module 14, reaffirmed in Module 18 with an automated guardrail.

## Context

Module 05 (Finance) built `apps.finance.models.wallet.WalletAccount`/
`WalletTransaction` + `apps.finance.services.wallet_service.WalletService`
as part of the initial Finance foundation: a per-`(tenant, party,
currency)` cached balance backed by an append-only transaction ledger,
with `HOLD`/`RELEASE`/`CREDIT`/`DEBIT`/`REFUND`/`ADJUSTMENT` types, links
to `FinancialDocument`/`PaymentTransaction`, and a DomainEvent published
on every mutation.

By Module 14, when real "Wallet & Customer Credits" requirements arrived
(overdraft configuration, idempotent transaction creation, `PROMOTION`/
`MANUAL` transaction types, explicitly *no* coupling to Finance documents
or settlement, *no* DomainEvent emission), Phase 1 inspection found the
Module 05 wallet had never been used by anything outside its own tests —
genuinely dormant scaffolding, not live functionality.

Building a second wallet concept (`apps.wallet.Wallet`) risked exactly
the kind of duplication this consolidation sprint exists to catch. The
module's own architecture-correction step considered three options:

1. Standardize on `apps.wallet`, mark the Finance version legacy.
2. Extend the Finance version in place.
3. Build a compatibility adapter over one canonical table.

Option 2 was rejected: extending the Finance wallet with overdraft/
idempotency/new types would change the semantics of its own existing
tests and require touching Finance, both explicitly out of scope. Option
3 was rejected as unnecessary complexity: the Finance wallet held zero
real data (nothing outside its tests ever created a row), so there was
nothing to migrate or reconcile.

## Decision

`apps.wallet` is the **sole, canonical, active** wallet bounded context.
`apps.finance.models.wallet`/`apps.finance.services.wallet_service` are
marked **legacy/frozen** via docstring — not deleted (their own tests
still exercise them and still pass), not refactored, not wired into
anything new. New code must never call `apps.finance.services
.WalletService`.

## Consequences

- Two "Wallet"/"WalletTransaction" model pairs exist in the codebase
  simultaneously, at different `db_table`s (`wallet_wallet` vs
  `finance_wallet_account`). This is intentional, not drift — see
  `docs/architecture/wallet-finance-boundary.md`.
- `apps.payments` (Module 15) and `apps.api`'s wallet endpoints (Module
  17B) both reference `apps.wallet` exclusively, confirming the decision
  held across two subsequent modules without needing re-litigation.
- Module 18 adds `NoDuplicateWalletModelTest`
  (`apps/kernel/tests/test_architecture_guardrails.py`) — an automated,
  source-level check that the only two locations in the codebase
  defining a model literally named `Wallet`/`WalletTransaction` are the
  two documented here. Any future accidental reintroduction of a third
  wallet concept now fails a test, rather than being caught (or missed)
  at the next audit.
