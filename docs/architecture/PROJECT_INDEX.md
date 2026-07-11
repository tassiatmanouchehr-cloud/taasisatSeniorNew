# Project Index

Status: current as of PR #29's merge (Epic 05 — Permission-Key Registry
& Authorization Hardening), `main` @
`9342c5880f33e604f7448b684bd031481ea2abd9` (PR #29's merge commit).

**Start here.** This is the entry point to this repository's
documentation — everything a new developer needs to understand where the
project stands, without reading old chats, old PRs, or prior
conversations.

---

## Read in this order

1. **[`PROJECT_STATE.md`](PROJECT_STATE.md)** — *"What is this, right
   now?"* Repository facts (versions, database, CI), every completed
   foundation in one page, the architecture rules already in force, and
   what development phase the project is in. Read this first, in full. It
   is the single source of truth for the project's current state.
2. **[`PROJECT_MODULE_STATUS.md`](PROJECT_MODULE_STATUS.md)** — *"What's
   built, against the original 25-module plan?"* A large table: every
   Blueprint module, its real status (Completed / Mostly Complete /
   Partial / Not Started), which app(s) implement it, which PR and commit
   shipped it, and what's left. Read this second, or jump straight to the
   row for whatever module you're about to touch.
3. **[`GAP_ANALYSIS.md`](GAP_ANALYSIS.md)** — *"What's actually missing,
   and how risky is it?"* Completed/partial/missing capabilities,
   technical debt, known limitations, fake providers, deferred
   architecture, and — most actionably — which modules should never
   change again, which need expansion, and which need refactoring. Read
   this third if you're deciding what to work on next.
4. **[`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)** — *"What should we
   build next, and why?"* The same gaps, organized by who benefits
   (Customer/Provider/Organization Experience, Platform Operations, Trust
   & Compliance, AI, Production, Enterprise) instead of by module number,
   each with purpose, business value, and priority. Read this fourth if
   you're planning, not just fixing.
5. **[`DECISION_HISTORY.md`](DECISION_HISTORY.md)** — *"Why does the code
   look like this?"* A one-page index of every ADR — what it decided, why,
   and whether it still holds. Read this when something in the code looks
   like it should be "fixed" and you want to check whether it's actually
   a deliberate, documented decision first.
6. **The [ADR folder](../adr/)** (`docs/adr/`) — the full reasoning behind
   each decision indexed in `DECISION_HISTORY.md`. Read the specific ADR
   for whatever area you're changing, not the whole folder end to end.
7. **The [Architecture folder](.)** (`docs/architecture/`) — the living
   reference docs this index lives alongside:
   [`system-overview.md`](system-overview.md),
   [`bounded-contexts.md`](bounded-contexts.md),
   [`dependency-graph.md`](dependency-graph.md),
   [`event-architecture.md`](event-architecture.md),
   [`rbac-permissions.md`](rbac-permissions.md),
   [`service-layer-guidelines.md`](service-layer-guidelines.md),
   [`api-guidelines.md`](api-guidelines.md),
   [`wallet-finance-boundary.md`](wallet-finance-boundary.md), and
   [`technical-debt-register.md`](technical-debt-register.md). Read
   whichever one covers the area you're working in; they're each short
   and single-purpose.
8. **Testing documentation** — `src/tests/visual/README.md` documents the
   Playwright visual/accessibility test suite. `.github/workflows/ci.yml`
   is the authoritative description of what CI actually runs (lint, UI
   quality gates, Tailwind build, the Django test suite, visual
   regression). A handful of early `src/SPRINT_*_VERIFICATION.md` files
   exist as historical snapshots from before the ADR system existed —
   useful for archaeology, not for current state (use `PROJECT_STATE.md`
   for that instead).

---

## The documents this repository now maintains

| Document | Answers |
|---|---|
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | Where are we right now? |
| [`PROJECT_MODULE_STATUS.md`](PROJECT_MODULE_STATUS.md) | What's built, module by module? |
| [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) | What's missing, and how risky is it? |
| [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md) | What should we build next? |
| [`DECISION_HISTORY.md`](DECISION_HISTORY.md) | Why does the code look like this? |
| [`docs/adr/`](../adr/) | The full reasoning behind each decision |
| [`docs/architecture/`](.) | Living, topic-by-topic reference docs |

---

## What this index is not

This is not a replacement for reading the code. It's the map that tells
you which code to read, and which decisions to trust rather than
re-litigate. If you find something in the code that contradicts a
document here, the document is either wrong (fix it) or the code is
(fix that, or write a new ADR if it's a deliberate, unrecorded change) —
but check `DECISION_HISTORY.md` before assuming either.
