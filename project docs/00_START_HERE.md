# سالمندیار — Enterprise Service Marketplace Platform

## What This Is

A multi-tenant Django platform for a senior-care service marketplace. Customers request in-home care services; independent providers and organizations deliver them. The platform mediates discovery, ordering, assignment, execution, payment, and review.

---

## Documentation Map

| # | Document | Purpose | Stability |
|---|---|---|---|
| 00 | **This file** | Entry point and reading order | Stable |
| 01 | `01_PRODUCT_SPECIFICATION.md` | What the platform does (business/product) | Stable |
| 02 | `02_SYSTEM_ARCHITECTURE.md` | How the platform is built (engineering) | Stable |
| 03 | `03_DOMAIN_WORKFLOWS.md` | How the platform works at runtime | Stable |
| 04 | `04_IMPLEMENTATION_STATUS.md` | Current state (changes every PR) | **Volatile** |
| 05 | `05_REPOSITORY_GOVERNANCE.md` | Rules, process, and maintenance policy | Stable |
| 06 | `06_DEVELOPMENT_AND_VERIFICATION.md` | Developer setup, build, test, lint | Semi-stable |
| 07 | `07_DEPLOYMENT_AND_OPERATIONS.md` | Production deployment and operations | Semi-stable |
| 08 | `08_TESTING_AND_QUALITY.md` | Test architecture and quality gates | Semi-stable |

### Supporting Records

| Location | Purpose | Update Pattern |
|---|---|---|
| `quality/COMPLETION_BACKLOG.md` | Active implementation gaps (BG-xxx) | Per-sprint |
| `quality/DEFECT_AND_RISK_REGISTER.md` | Active risks and defects (FR/KL/RISK) | As discovered |
| `traceability/ARCHITECTURE_DECISION_LOG.md` | Architecture decisions (ADM-xxx) | Append-only |
| `traceability/IMPLEMENTATION_JOURNAL.md` | Sprint-by-sprint history | Append-only |
| `traceability/CHANGE_LEDGER.md` | Change records (CL-xxx) | Append-only |
| `assessments/*.md` | Immutable code-review evidence | Never modified |

---

## Mandatory Reading Order

1. **This file** — orientation
2. **01_PRODUCT_SPECIFICATION.md** — understand what the platform is
3. **02_SYSTEM_ARCHITECTURE.md** — understand how it's engineered
4. **03_DOMAIN_WORKFLOWS.md** — understand runtime behavior
5. **04_IMPLEMENTATION_STATUS.md** — understand where we stand now
6. Then, based on your role:
   - **Developer:** 06_DEVELOPMENT_AND_VERIFICATION.md
   - **Operator:** 07_DEPLOYMENT_AND_OPERATIONS.md
   - **QA/Reviewer:** 08_TESTING_AND_QUALITY.md
   - **Architect:** traceability/ARCHITECTURE_DECISION_LOG.md

---

## Source of Truth Hierarchy

1. **Repository source code** (models, services, tests, migrations) — highest authority
2. **04_IMPLEMENTATION_STATUS.md** — current state snapshot
3. **01–03, 05–08** — stable reference documentation
4. **quality/** and **traceability/** — operational records
5. **assessments/** — historical evidence (immutable, never overrides current state)

When code and documentation disagree: **code wins**. Update the documentation.

---

## Current Repository Status

See `04_IMPLEMENTATION_STATUS.md` for:
- Current HEAD and branch
- Test baseline (2,546/2,546 passing)
- CI status
- What's implemented vs. missing
- Next recommended action

---

## Quick Start (Developer)

See `06_DEVELOPMENT_AND_VERIFICATION.md` for full instructions. Summary:

```bash
cd src/
cp .env.example .env
python -m pip install -r requirements/base.txt
python manage.py migrate
python manage.py seed_tenant && python manage.py seed_auth_roles
python manage.py seed_service_catalog && python manage.py seed_product_walkthrough --reset-demo
python manage.py runserver
# Open http://127.0.0.1:8000/
```

---

## Rules for AI Coding Agents

1. Read `05_REPOSITORY_GOVERNANCE.md` before making any change
2. Source code is the highest authority — verify documentation claims against code
3. Never implement features not authorized by the current roadmap phase
4. Every implementation milestone requires: assessment → documentation sync → baseline update
5. Do not create new documentation outside the canonical structure above
