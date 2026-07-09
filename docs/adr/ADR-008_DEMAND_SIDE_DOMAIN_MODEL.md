# ADR-008 — Demand-Side Domain Model: One Requester, Not One Account Per Beneficiary

## Status

Accepted — Module 21A (Authentication UX & Multi-Role Account Model Fix).

## Context

Module 21A's brief included a demo-account seed list with a "Family
Member" persona (`family@salmandyar.local`), alongside the module's
broader multi-role goal: one `Person`/`UserAccount` should be able to
hold several roles (customer, caregiver, organization admin, etc.)
without duplicate accounts. While seeding that persona, the natural
question arose: how should "a family member requesting/following care on
behalf of someone else" actually be modeled?

Two options were on the table:

1. A `FamilyMemberProfile` (or similar) — a distinct profile/account type
   representing a family member, separate from `CustomerProfile`.
2. No new profile type at all — the requester is always a single
   `CustomerProfile`-holding `UserAccount`; who the service is *for* is a
   property of the order, not of the account.

Product clarification settled this explicitly: there is only ever **one
authenticated requester account**. "I need a nurse for myself," "I need a
physiotherapist for my father," and "I need a caregiver for my mother"
are the *same* kind of event from the account model's point of view — one
customer, placing one order, on behalf of some care recipient (who may or
may not be themselves). The care recipient is data on the order, not a
second account.

Separately, the question of a third party (e.g. a sibling) wanting to
*follow* an order the primary customer placed raised the same temptation
— give the sibling their own account/profile scoped to that order. Product
clarification rejected this too: the correct future shape is a scoped,
revocable **share link** for that one order, not a new account.

## Decision

- **Do not introduce a `FamilyMemberProfile`** (or any other
  profile/account type representing "a family member" as a distinct kind
  of user). `apps.accounts.models.profiles` gains no new profile model
  from this ADR.
- The demand side of the platform has exactly one authenticated role that
  places orders: the customer, holding one `CustomerProfile` per
  `UserAccount` (per the existing multi-role model — see
  `ensure_customer_profile()` in `apps.accounts.services.profiles`,
  Module 21A). "Family member" is not a role or profile; it is simply
  another customer account, or a relationship value on an order.
- **Future work (not built in this module):** `CareRecipient` is a
  first-class, **reusable** domain entity — not something embedded in, or
  owned by, `Order`. A customer requests services for the same father,
  mother, spouse, child, or grandparent repeatedly, potentially over many
  years; a `CareRecipient` created once must be selectable by every
  future order, not re-entered or re-modeled per order. The intended
  ownership chain:

  ```
  Customer (UserAccount)
          │
          ▼
  CustomerProfile
          │
          ▼
  CareRecipient
          │
          ├── demographics
          ├── medical notes
          ├── addresses
          ├── emergency contacts
          ├── preferences
          ├── consent records
          └── historical orders
  ```

  `CareRecipient` belongs to its own bounded context (`apps.accounts`, as
  a sibling of `CustomerProfile`/`ElderProfile`, or a dedicated future
  app — not decided here), reachable from `CustomerProfile`. **Orders
  will eventually reference an existing `CareRecipient` instead of
  embedding recipient information** — `Order` gains:
  - `requested_by` — the authenticated `CustomerProfile`/`UserAccount`
    that owns the order (already exists today as `Order.customer_profile`).
  - `care_recipient` — FK to the reusable `CareRecipient`.
  - `relationship_to_recipient` — one of `self`, `father`, `mother`,
    `spouse`, `child`, `sibling`, `grandparent`, `relative`, `friend`,
    `legal_guardian`, `other` (recorded per-order since a recipient's
    relationship label could theoretically be corrected without meaning
    a different person, though in practice it's stable per recipient).

  A customer account may own multiple `CareRecipient`s (e.g. Father,
  Mother, Grandmother all under one `CustomerProfile`), and each future
  order simply selects one.
- **Family members do not become authenticated accounts automatically.**
  Whether the person a `CareRecipient` represents ever gets their own
  login is a separate, unrelated question from `CareRecipient` existing
  as data — nothing about modeling a reusable care recipient implies or
  requires provisioning a `UserAccount` for them.
- **Future work (not built in this module):** an **Order Share Link**
  mechanism. Shared order access remains **invitation-based and limited
  to one order** — the owning customer generates a secure, scoped link
  granting a single named order's visibility to someone who is not an
  authenticated platform user in any broader sense. A share-link viewer:
  - can view only the one shared order;
  - cannot modify the order, create new orders, or access wallet,
    payments, the owner's profile, other orders, or personal settings.

  This is explicitly a read-only, single-order visibility grant — not a
  new account type, not a new role, not a second `CustomerProfile`, and
  not a general-purpose "family follows customer" relationship.

## Consequences

- `apps.accounts.management.commands.seed_demo_accounts`'s
  `family@salmandyar.local` demo persona remains exactly what it already
  was implemented as: an ordinary `CustomerProfile`-holding account (via
  `ensure_customer_profile()`), no different in kind from
  `customer@salmandyar.local`. It is a demo *persona label*, not evidence
  of a "family member" account type — nothing to change there.
- `CustomerProfile.relation_to_elder` (Module 08-era free-text field,
  pre-dating this ADR) remains as-is; it describes the requester's
  relationship to the elder they manage under today's `ElderProfile`
  model. It is not the same field as the future `Order.
  relationship_to_recipient` described above and is not being unified
  with it in this module — reconciling `ElderProfile` with the future
  reusable `CareRecipient` (they look like overlapping concepts) is
  explicitly left to the future `CareRecipient` module to resolve, not
  decided here.
- No schema changes result from this ADR. It is a decision record only,
  scoping what Module 21A did *not* build and constraining what a future
  `CareRecipient`/Order-Share-Link module should build: `CareRecipient`
  as a reusable entity reachable from `CustomerProfile` that `Order`
  references by FK — not an `Order`-owned, per-order-embedded concept,
  and not a family-member account concept.
- Any future PR introducing a model literally representing "a family
  member" as an account/profile type should be treated as a violation of
  this ADR and point back here.
