# سالمندیار (Salmandyar, "Elder Companion") — Enterprise Service Marketplace Platform

A multi-tenant Django platform for a senior-care service marketplace.
Customers request in-home care services; independent providers and
organizations (with their own caregivers) deliver them. The platform
coordinates identity, matching, booking, execution, pricing, payment,
reviews, and reporting across that lifecycle.

The Django project lives in [`src/`](src/). See
[`src/RUN_NATIVE_NO_VENV.md`](src/RUN_NATIVE_NO_VENV.md) for local setup.

---

## Project Documentation

This repository is self-documenting. The documents below are the
**official project navigation system** — read them to understand where
the project stands, what's built, what's missing, and what to build next,
without needing any prior conversation or PR history.

**Start here: [`docs/architecture/PROJECT_INDEX.md`](docs/architecture/PROJECT_INDEX.md)**

| Document | Answers |
|---|---|
| [`PROJECT_INDEX.md`](docs/architecture/PROJECT_INDEX.md) | Where do I start, and in what order? |
| [`PROJECT_STATE.md`](docs/architecture/PROJECT_STATE.md) | Where are we right now? (versions, CI, completed foundations, architecture rules, current phase) |
| [`PROJECT_MODULE_STATUS.md`](docs/architecture/PROJECT_MODULE_STATUS.md) | What's built, against the original 25-module Blueprint? |
| [`GAP_ANALYSIS.md`](docs/architecture/GAP_ANALYSIS.md) | What's missing, and how risky is it? |
| [`PRODUCT_ROADMAP.md`](docs/architecture/PRODUCT_ROADMAP.md) | What should we build next, organized by business value? |
| [`DECISION_HISTORY.md`](docs/architecture/DECISION_HISTORY.md) | Why does the code look like this? (index of every ADR) |
| [`docs/adr/`](docs/adr/) | The full reasoning behind each architecture decision |
| [`docs/architecture/`](docs/architecture/) | Living, topic-by-topic reference docs (bounded contexts, dependency graph, event architecture, RBAC, service-layer rules, API guidelines, technical debt) |

A new developer should be able to understand what's implemented, what's
partially implemented, what hasn't been started, the current architecture
and its binding rules, and the roadmap — in under 15 minutes, starting
from `PROJECT_INDEX.md` alone.
