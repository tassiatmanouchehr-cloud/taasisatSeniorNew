# TESTING AND QUALITY

## Test Taxonomy

| Category | Count | Location | Framework |
|---|---|---|---|
| Unit/Service tests | 2,546 methods | `src/apps/*/tests/` | Django TestCase |
| Concurrency tests | 44 (12 files) | `src/apps/*/tests/` | TransactionTestCase + threading |
| Architecture guardrails | 28 tests | `src/apps/kernel/tests/test_architecture_guardrails.py` | SimpleTestCase (source scan) |
| Permission registry guards | (in kernel) | `src/apps/kernel/tests/test_permission_registry_guardrails.py` | SimpleTestCase |
| Visual regression | 525 baselines | `src/tests/visual/baselines/` | Playwright |
| Accessibility | 2 specs | `src/tests/visual/specs/` | Playwright + axe-core |
| Mobile navigation | 1 spec | `src/tests/visual/specs/` | Playwright |

## Architecture Guardrail Tests

These automated tests scan source code to enforce architectural rules:

| Test Class | Enforces |
|---|---|
| `ApiViewOrmDisciplineTest` | No direct ORM in API views |
| `AdminPortalOrmDisciplineTest` | No direct ORM in admin portal views |
| `PortalOrmDisciplineTest` | No direct ORM in customer portal views |
| `ProviderPortalOrmDisciplineTest` | No direct ORM in provider portal views |
| `OrganizationPortalOrmDisciplineTest` | No direct ORM in organization portal views |
| `PublicSiteOrmDisciplineTest` | No direct ORM in public site views |
| `NoReverseApiImportTest` | Nothing imports apps.api (leaf node) |
| `NoDuplicateWalletModelTest` | Wallet models only in documented locations |
| `EventSystemSeparationTest` | Only publisher/worker touch EventOutbox |
| `ServiceSupplierProfileCouplingTest` | Limited direct profile imports outside accounts |
| `OrderOrganizationEligibilitySoleWriterTest` | Only eligibility service writes to that model |
| `ProfileStatusTransitionSoleWriterTest` | Only activation service transitions profile status |
| `ServiceSupplierSoleWriterTest` | Only supplier_registry creates/modifies suppliers |
| `RbacEnforcementEmergencyControlTest` | Admin portal never directly touches ConfigurationValue |

## Concurrency Tests

12 dedicated test files using `TransactionTestCase` with real multi-threaded execution:

- Affiliation one-active-at-a-time (cross-organization race)
- Gallery item limit enforcement under concurrent upload
- Document resubmission race
- Profile activation (two concurrent activations)
- Verification rollup (two concurrent reviews)
- Availability window overlap prevention
- Booking assignment double-assign prevention
- Commission contract activation race
- Supplier registry uniqueness constraint
- Order number collision retry
- Payment settlement orchestration
- Supplier supplier concurrent creation

## CI Workflows

### `.github/workflows/ci.yml`

| Job | Purpose | Runs On |
|---|---|---|
| **Lint & Format Check** | `ruff check` + `ruff format --check` | ubuntu-latest |
| **UI Quality Gates** | validate_tokens, validate_rtl, validate_themes, validate_components | ubuntu-latest |
| **Tailwind CSS Build** | Compile CSS + JS, verify output exists | ubuntu-latest (Node 22) |
| **Django Test Suite** | `manage.py check` + `manage.py test` | ubuntu-latest + PostgreSQL 16 + Redis 7 |
| **Visual & Accessibility Tests** | Playwright specs (accessibility + visual comparison) | ubuntu-latest + PostgreSQL + Redis + Node |

### `.github/workflows/generate-visual-baselines.yml`

Manual dispatch workflow for regenerating the 525 visual baseline PNGs. See "Visual Baseline Management" below.

## Migration Checks

- `manage.py check` — must report 0 issues
- `makemigrations --check --dry-run` — known to exit 1 due to RISK-009 (pre-existing cosmetic drift in `kernel` app; `help_text`/`verbose_name` metadata only, no schema change)
- `manage.py migrate --check` — must report no unapplied migrations

## Linting

- Tool: Ruff (configured in `pyproject.toml`)
- Line length: 120
- Target: Python 3.12
- Select rules: E, F, W, I, N, UP, B, A, COM, C4, DJ, T20, SIM
- Per-file ignores for tools/, management commands, `__init__.py`

## Test Baseline Policy

The full regression count is recorded in `04_IMPLEMENTATION_STATUS.md` after every significant merge. Current: **2,546/2,546 PASS**.

### When to Update the Baseline

- After any PR that adds new tests
- After any PR that removes deprecated tests
- Never after a PR that merely fixes a test without changing count

## Visual Baseline Management

### 525 PNG Baselines

Generated across 7 Playwright projects (3 viewports × 2-3 color schemes × 2 locales):
- desktop-light-rtl, desktop-dark-rtl, desktop-light-ltr
- tablet-light-rtl, tablet-dark-rtl
- mobile-light-rtl, mobile-dark-rtl

### When to Regenerate

- After UI component design changes
- After Tailwind/CSS token modifications
- After Playwright or browser version upgrades
- After font changes
- After CI runner OS major version changes

### Regeneration Process

1. Navigate to GitHub Actions → "Generate Visual Baselines"
2. Click "Run workflow" (manual dispatch)
3. Download the `playwright-baselines` artifact
4. Verify: 525 PNGs, zero empty files, zero corrupt
5. Human-review representative samples
6. Replace `src/tests/visual/baselines/` contents
7. Commit as a dedicated PR

### Canonical Generation Environment

- OS: Ubuntu (GitHub-hosted `ubuntu-latest`)
- Python: 3.12, Node: 22
- Playwright: ^1.44 (Chromium + WebKit)
- Database: PostgreSQL 16 + PostGIS
- Fonts: System fallback (platform fonts not committed)

## Phase Acceptance Criteria

Every implementation phase must satisfy before closure:

1. All roadmap acceptance criteria met
2. Full regression passes (all tests green)
3. `manage.py check` reports 0 issues
4. `git diff --check` is clean
5. Documentation synchronized per governance §18
6. New test count recorded in `04_IMPLEMENTATION_STATUS.md`
7. No known regression introduced

## Required Checks Before Merge

- [ ] All 5 CI jobs pass (lint, UI quality, Tailwind build, Django tests, visual/accessibility)
- [ ] `git diff --check` clean
- [ ] Documentation synchronized if behavior changed
- [ ] No unrelated code in the diff

## Required Checks After Merge

- [ ] `04_IMPLEMENTATION_STATUS.md` updated if test count changed
- [ ] `quality/COMPLETION_BACKLOG.md` updated if a gap was closed
- [ ] `quality/DEFECT_AND_RISK_REGISTER.md` updated if a risk was mitigated
- [ ] `traceability/IMPLEMENTATION_JOURNAL.md` appended for milestones

## UI Quality Validation Tools

4 custom validation scripts in `src/tools/`:

| Script | Purpose |
|---|---|
| `validate_tokens.py` | Verify design token consistency across themes |
| `validate_rtl.py` | Verify RTL compliance in templates |
| `validate_themes.py` | Verify theme variable completeness (83 vars) |
| `validate_components.py` | Verify component architecture rules |

All run as part of the "UI Quality Gates" CI job.
