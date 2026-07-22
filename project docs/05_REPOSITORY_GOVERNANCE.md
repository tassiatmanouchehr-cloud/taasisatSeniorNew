# REPOSITORY GOVERNANCE

## Source-of-Truth Hierarchy

1. Current source code, migrations, and tests
2. `04_IMPLEMENTATION_STATUS.md` — canonical current-state snapshot
3. `01_PRODUCT_SPECIFICATION.md`, `02_SYSTEM_ARCHITECTURE.md`, `03_DOMAIN_WORKFLOWS.md` — stable reference
4. `quality/COMPLETION_BACKLOG.md` and `quality/DEFECT_AND_RISK_REGISTER.md` — active operational trackers
5. `traceability/ARCHITECTURE_DECISION_LOG.md` — architectural rationale
6. `traceability/IMPLEMENTATION_JOURNAL.md` and `CHANGE_LEDGER.md` — historical record
7. `assessments/*.md` — immutable evidence (consult for detail behind a baseline, never as a substitute for current state)

When code and documentation conflict: **code wins**. Update the documentation immediately.

---

## Mandatory Repository Governance Rule (§18)

> **Every significant implementation milestone or Epic completion must conclude with, in order:**
>
> 1. **Repository assessment** — evidence-based, verified against current code and tests (never assumed from prior documentation).
> 2. **Documentation synchronization** — every active document whose claims the milestone changed is corrected in place; stale language is removed, not merely footnoted.
> 3. **Implementation status update** — `04_IMPLEMENTATION_STATUS.md` is updated to reflect the new current state.
> 4. **Next-milestone determination** — the next recommended action is re-derived from fresh evidence, never carried forward by default.
>
> This is binding on all future work in this repository and supersedes any conflicting informal practice.

---

## Pre-Implementation Rules

- Do not implement features not authorized by the current roadmap phase
- Do not begin implementation without completing a code-free Architecture Assessment when the phase requires one
- Do not redesign stable architecture without explicit approval
- Do not create branches for production work before assessment approval

## Phase Acceptance Rules

A phase is not complete until:

1. All acceptance criteria in `IMPLEMENTATION_ROADMAP.md` are satisfied
2. Full regression passes
3. `manage.py check` reports 0 issues
4. `git diff --check` is clean
5. Documentation is synchronized per §18 above
6. The completion is recorded in `04_IMPLEMENTATION_STATUS.md`

## Branch and Commit Policy

- Feature work on named branches (e.g., `feat/order-offer-submission-lifecycle`)
- Never push directly to `main` unless explicitly instructed
- Commit messages follow conventional format: `type(scope): description`
- Documentation-only commits: `docs: description`

## PR Review Requirements

- All CI checks must pass before merge
- Documentation synchronization must be included in the same PR or immediately following
- Architecture review required for: new models, new migrations, new permission keys, new service-layer patterns

## Migration Policy

- One migration per logical change (never multiple for the same schema change)
- Data migrations must be reversible or documented as irreversible
- `makemigrations --check --dry-run` must show only documented pre-existing drift (RISK-009)

## Test Policy

- Every new service method requires focused tests
- Every new permission key requires enforcement + denial tests
- Concurrency-sensitive mutations require `TransactionTestCase` tests
- Full regression run required before merge when: new model, new migration, shared service change, security boundary change

## Security Review Expectations

- Any change to `PermissionService`, RBAC, or tenant isolation requires explicit security review
- New permission keys must be registered in `apps/kernel/permissions/keys.py`
- No permission key may exist without a real enforcement call site

## Documentation Synchronization Requirements

After every merged PR that changes behavior:

1. Update `04_IMPLEMENTATION_STATUS.md` if test counts, module status, or risks changed
2. Update `quality/COMPLETION_BACKLOG.md` if a gap was closed
3. Update `quality/DEFECT_AND_RISK_REGISTER.md` if a defect was fixed or risk mitigated
4. Append to `traceability/IMPLEMENTATION_JOURNAL.md` for significant milestones
5. Append to `traceability/CHANGE_LEDGER.md` for every documentation change

## Rules for AI Coding Agents

1. Read this file and `04_IMPLEMENTATION_STATUS.md` before any work
2. Source code is the highest authority — verify every claim before trusting it
3. Never implement features not authorized by current roadmap phase
4. Never document intended future behavior as implemented
5. Never silently skip the §18 governance rule
6. Report conflicts between documentation and code rather than guessing
7. Do not create documentation outside the canonical structure defined in `00_START_HERE.md`
