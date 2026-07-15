# TEST EXECUTION LOG

**Repository:** taasisatSenior
**Session:** Offer Marketplace Analysis and Contract Development

---

## Run 001 — Full Django Test Suite

```
Command: python manage.py test --verbosity=2
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Environment variables: DATABASE_ENGINE=django.db.backends.postgresql, GIS_ENABLED=false
Working directory: C:\Users\hp\Desktop\MIMO\1\taasisatSenior\src
Date/time: 2026-07-13
```

| Metric | Value |
|--------|-------|
| Total tests found | 1632 |
| Passed | 1632 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Duration | 320.613 seconds |
| Result | OK |

**Relevant output:**
```
Found 1632 test(s).
Creating test database for alias 'default' ('test_marketplace')...
... (1632 tests) ...
Ran 1632 tests in 320.613s
OK
Destroying test database for alias 'default'...
```

**Environmental deviations:** None. PostgreSQL 16 running locally on port 5432. GIS_ENABLED=false (no PostGIS).

---

## Run 002 — E2E Validation Script (Attempt 1-6, Failures)

```
Command: python e2e_validation.py
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (marketplace, persistent)
Working directory: C:\Users\hp\Desktop\MIMO\1\taasisatSenior\src
Date/time: 2026-07-13
```

| Metric | Value |
|--------|-------|
| Total steps | 18 |
| Passed (final run) | 18 |
| Failed (script development) | 6 attempts with parameter errors |

**Note:** This is a standalone validation script, not part of the official Django test suite. Failures were in script inputs (wrong function signatures, missing permissions), not in production code.

---

## Run 003 — Django System Check

```
Command: python manage.py check
Result: System check identified no issues (0 silenced)
```

---

## Run 004 — Migration Check

```
Command: python manage.py makemigrations --check --dry-run
Result: Cosmetic drift detected (accounts: 7 Alter field changes, kernel: 50+ Alter field/index changes)
Nature: Django version-skew artifact. manage.py migrate reports "no migrations to apply" for these.
```

---

## Run 005 — Database Migration (Fresh)

```
Command: python manage.py migrate
Result: 55 migrations applied successfully
Range: contenttypes.0001_initial through wallet.0001_initial
```

---

## Future Test Executions

Append future test runs below this line.

---

## Run 006 — Phase 1 Remediation: manage.py check

```
Command: python manage.py check
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f (unchanged)
Settings module: config.settings.testing
Database: PostgreSQL 16
Date/time: 2026-07-14
Exit code: 0
```

| Metric | Value |
|--------|-------|
| Result | System check identified no issues (0 silenced) |

---

## Run 007 — Phase 1 Remediation: makemigrations --check

```
Command: python manage.py makemigrations --check --dry-run
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16
Date/time: 2026-07-14
Exit code: 1 (expected — cosmetic accounts/kernel drift)
```

| Metric | Value |
|--------|-------|
| Accounts drift | 7 Alter field changes (cosmetic metadata) |
| Kernel drift | 50+ Alter field/index changes (cosmetic metadata) |
| Orders migration proposed | **None** |
| Nature | Django version-skew artifact. No real schema changes. |

---

## Run 008 — Phase 1 Remediation: OrderOffer Targeted Tests

```
Command: python manage.py test apps.orders.tests.test_order_offer_model --verbosity=2
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
Exit code: 0
```

| Metric | Value |
|--------|-------|
| Total tests found | 40 |
| Passed | 40 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Duration | 1.494 seconds |
| Result | OK |

---

## Run 009 — Phase 1 Remediation: Full Orders Tests

```
Command: python manage.py test apps.orders.tests --verbosity=1
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
Exit code: 0
```

| Metric | Value |
|--------|-------|
| Total tests found | 119 |
| Passed | 119 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Duration | 9.037 seconds |
| Result | OK |

---

## Run 010 — Phase 1 Remediation: Full Regression Suite

```
Command: python manage.py test --verbosity=1
Commit SHA: a5dbaf28703142edaa1d770ea8f3c2a45a12640f
Settings module: config.settings.testing
Database: PostgreSQL 16 (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
Exit code: 1
```

| Metric | Value |
|--------|-------|
| Total tests found | 1672 |
| Passed | 1671 |
| Failed | 0 |
| Errors | 1 |
| Skipped | 0 |
| Duration | 351.569 seconds |
| Result | FAILED (1 error) |

**Error details:**
```
ERROR: test_reporting_does_not_change_service_supplier_count
  (apps.kernel.tests.test_seed_product_walkthrough.SeedProductWalkthroughReportSideEffectTest)
Cause: IntegrityError — duplicate order_number (ORD-20260713-7329)
Location: seed_product_walkthrough.py line 928 → create_operator_order
Nature: Pre-existing race condition in seed command. order_number auto-generation
         uses random 4-digit suffix that can collide within same second.
         NOT related to OrderOffer model or Phase 1 changes.
```

---

## Run 008 — Current-HEAD Verification (Documentation Sync Task)

```
Commit SHA: ce3b30e0f3c06d7b058587f3e75c357bfe588415 (main)
Branch during verification: claude/taasisat-senior-state-verify-9dzzlm
  (= ce3b30e + documentation-only commit ed33e47, IMPLEMENTATION_ROADMAP.md;
   no src/ differences vs ce3b30e)
Git status before verification: working tree clean
Settings module: config.settings.testing
Environment: cloud verification container
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13 (Ubuntu 24.04)
Database: PostgreSQL (test_marketplace, auto-created and destroyed)
Date/time: 2026-07-14
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift (accounts ×8 field alters, kernel manager/index-rename/field alters) — same behavior recorded in CL-013 at previous HEAD |
| `python manage.py migrate` | 0 | All migrations apply cleanly, including orders.0008_orderoffer |
| Seed test isolated ×10 (`SeedProductWalkthroughReportSideEffectTest.test_reporting_does_not_change_service_supplier_count`) | 9×0, 1×1 | Run 10 failed IN ISOLATION: IntegrityError duplicate order_number `ORD-20260714-1003` |
| `python manage.py test --verbosity=1` (full suite) | 1 | Ran 1662, FAILED (errors=2). Both errors: duplicate order_number in seed walkthrough (`SeedProductWalkthroughDatasetTest.setUpClass` — its 10 tests therefore not run, explaining 1662 vs 1672 — and `SeedProductWalkthroughReportSideEffectTest`) |

**Failure analysis:** Both failures are the known seed order_number collision:
`orders/models.py:_generate_order_number()` uses a 4-digit random suffix; the
seed walkthrough creates enough same-day orders that in-run collisions occur
randomly (birthday problem). The 1/10 isolated-run failure proves this is a
RANDOM IN-RUN COLLISION, not an inter-test race or order-dependent effect.
`git show ce3b30e` confirms neither `_generate_order_number()` nor the seed
command was modified by ce3b30e (last seed change: 697d7ea) — PRE-EXISTING.

**Classification of HEAD ce3b30e:**
`GREEN_EXCEPT_CONFIRMED_PRE_EXISTING_FLAKY_TEST` — all 1660 executed
non-seed-affected tests passed; the only failures trace to the pre-existing
random collision (BG-002).

---

## Run 009 — BG-002 Fix Verification

```
Base commit: bc252fe (branch claude/taasisat-senior-state-verify-9dzzlm,
  documentation-only ahead of main ce3b30e) + BG-002 fix in working tree
Settings module: config.settings.testing
Environment: cloud verification container
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-14
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | No issues |
| `python manage.py makemigrations --check --dry-run` | 1 | UNCHANGED pre-existing cosmetic drift (accounts/kernel only, ZERO orders entries) — the fix requires no migration |
| New regression tests (`apps.orders.tests.test_order_number_generation`, verbosity 2) | 0 | 8/8 OK incl. TransactionTestCase concurrency test |
| `python manage.py test apps.kernel.tests.test_seed_product_walkthrough --verbosity=2` | 0 | Ran 46 tests — OK (previously failed intermittently) |
| `python manage.py test apps.orders.tests --verbosity=1` | 0 | Ran 127 tests — OK (119 prior + 8 new) |
| Previously flaky isolated test ×20 | 20×0 | 20/20 PASS (pre-fix: 1/10 failed in isolation) |
| `python manage.py test --verbosity=1` (full suite) | 0 | **Ran 1680 tests in 92.9s — OK** (1672 pre-existing + 8 new; first fully green full regression on record) |

**Conclusion:** BG-002 resolved. Full regression exits 0. The
makemigrations drift remains the only pre-existing exit-1 command and is
unrelated to this fix.

---

## Run 010 — Phase 1.1 Manual Document Verification

```
Branch: phase1-registration-manual-verification (from main @ 55b1cb0)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only (accounts/kernel field alters, unrelated to this change) — same as before this task |
| `python manage.py migrate` | 0 | accounts.0005 applies cleanly |
| `apps.accounts.tests.test_verification_review` | 0 | 25/25 (incl. `VerificationReviewConcurrencyTest`, `TransactionTestCase`) |
| `apps.admin_portal.tests.test_document_verification` | 0 | 16/16 |
| `apps.accounts.tests.test_registration` (existing) | 0 | 8/8 — customer/caregiver/organization registration unaffected |
| `apps.accounts` (full app suite) | 0 | 205/205 (180 pre-existing + 25 new) |
| `apps.admin_portal` (full app suite) | 0 | 45/45 (29 pre-existing + 16 new) |
| `apps.kernel` (full app suite) | 0 | 232/232 (permission registry/role catalog change verified safe) |
| `apps.provider_portal apps.organization_portal apps.public_site` | 0 | 182/182 (touched shared templates verified safe) |
| **Full regression** | **0** | **Ran 1721 tests — OK** (1680 baseline + 41 new) |

**Classification:** GREEN — all 41 new tests pass, zero regressions in 1680 pre-existing tests, migration drift unchanged from pre-task baseline.

---

## Run 011 — Phase 1.2 Verification Completion and Activation Rules

```
Branch: phase1-verification-activation-rules (from main @ 278098b)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only (accounts/kernel field alters, unchanged from before this task) |
| `apps.accounts.tests.test_verification_policy` | 0 | 13/13 |
| `apps.accounts.tests.test_verification_rollup` | 0 | 13/13 (incl. `RollupConcurrencyTest`, `TransactionTestCase`) |
| `apps.accounts.tests.test_document_resubmission` | 0 | 10/10 (incl. `ResubmissionConcurrencyTest`, `TransactionTestCase`) |
| `apps.accounts.tests.test_activation_eligibility` | 0 | 11/11 |
| `apps.accounts.tests.test_verification_review` (existing, Phase 1.1) | 0 | 25/25 — no regression from roll-up sync wiring |
| `apps.accounts` (full app suite — Level 2) | 0 | 252/252 (205 baseline + 47 new) |
| `apps.provider_portal apps.organization_portal` (Level 2 — resubmit() call-site change) | 0 | 102/102 |
| **Full regression (Level 3 — transaction/concurrency behavior changed + shared-service, multi-app workflow)** | **0** | **Ran 1768 tests — OK** (1721 baseline + 47 new) |

**Test level used:** Level 3 (full regression), justified by: `resubmit()`/`sync_*()`
introduce new `select_for_update()` locking (concurrency behavior change); the workflow
change spans `accounts` + `provider_portal` + `organization_portal` (3 apps) through one
shared-service change (`DocumentService`, `VerificationReviewService`).

**Classification:** GREEN — all 47 new tests pass, zero regressions in 1721 pre-existing
tests, migration drift unchanged from pre-task baseline (no new migration).

---

## Run 012 — Phase 1.3 Complete Phase 1 Activation and Profile Completion

```
Branch: phase1-activation-completion-final (from main @ 860640e)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.accounts.tests.test_profile_completion` | 0 | 11/11 |
| `apps.accounts.tests.test_profile_activation` | 0 | 16/16 (incl. `ConcurrentActivationTest`, `TransactionTestCase`) |
| `apps.admin_portal.tests.test_profile_activation` | 0 | 9/9 |
| `apps.provider_portal.tests.test_activation_presentation` | 0 | 2/2 |
| `apps.organization_portal.tests.test_activation_presentation` | 0 | 2/2 |
| `apps.accounts apps.provider_portal apps.organization_portal apps.admin_portal` (Level 2 — all directly affected apps) | 0 | 439/439 (incl. two locked query-count baselines updated: provider_portal 7->10, organization_portal 7->11, both fixed-cost, not per-item — see ARCHITECTURE_DECISION_LOG ADM-016) |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged from before this task (no new accounts/kernel entries) |
| **Full regression (Level 3 — shared activation behavior across 3 apps, new platform-scoped RBAC permission, new select_for_update() concurrency locking, medium-risk Phase-1-closing merge prep)** | **0** | **Ran 1808 tests — OK** (1768 baseline + 40 new) |

**Test level used:** Level 3 (full regression), run exactly once before PR creation, justified
by: activation behavior is shared across `accounts`/`provider_portal`/`organization_portal`/
`admin_portal` (4 apps); a new permission/RBAC key (`ACCOUNTS_PROFILE_ACTIVATE`) was added to
the canonical registry and role catalog; `ProfileActivationService` introduces new
`select_for_update()` row-locking (transaction/concurrency behavior change); this PR closes
Phase 1 — a medium/high-risk merge-prep trigger in its own right.

**Classification:** GREEN — all 40 new tests pass, zero regressions in 1768 pre-existing
tests (two intentional, documented query-count baseline updates in pre-existing tests, not
failures — the new fixed-cost activation-status lookup on the profile page), migration
drift unchanged from pre-task baseline (no new migration).

---

## Run 013 — Phase 1.3 Remediation: Fix Activation State Semantics (PR #5)

```
Branch: phase1-activation-completion-final (from main @ 860640e)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.accounts.tests.test_profile_completion` | 0 | 11/11 (unchanged, unaffected) |
| `apps.accounts.tests.test_profile_activation` | 0 | 24/24 (rewritten: DRAFT fixtures, `ProfileActivationResult` assertions, `AuditLogIsNotSourceOfTruthTest`, `EligibilitySemanticsTest`, organization-suspended coverage, incl. `ConcurrentActivationTest`) |
| `apps.accounts.tests.test_activation_eligibility` | 0 | 15/15 (reason-code rename verified; archived/draft-eligible/organization-suspended coverage added) |
| `apps.accounts.tests.test_registration` | 0 | 10/10 (incl. 2 new DRAFT-on-registration assertions) |
| `apps.admin_portal.tests.test_profile_activation` | 0 | 11/11 (incl. 2 new suspended-activation tests) |
| `apps.provider_portal.tests.test_activation_presentation` | 0 | 2/2 (DRAFT fixture fix) |
| `apps.organization_portal.tests.test_activation_presentation` | 0 | 2/2 (same) |
| `apps.accounts apps.admin_portal apps.provider_portal apps.organization_portal` (Level 2 — all directly affected apps) | 0 | 455/455 (incl. 2 locked query-count baselines updated: provider_portal 10->9, organization_portal 11->10 — `is_activated()` no longer queries `AuditLog`) |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged; confirmed no `CaregiverProfile`/`OrganizationProfile.status` field entry present (model-level default intentionally unchanged) |
| **Full regression (Level 3 — registration bootstrap changed, profile-status semantics changed, transaction/concurrency-adjacent service rewritten, spans 4+ apps)** | **0** | **Ran 1824 tests — OK** (1808 baseline + 16 new/renamed) |

**Test level used:** Level 3 (full regression), run exactly once before updating PR #5,
justified by: this remediation changes what status a real user's caregiver/organization
profile starts in (registration bootstrap — a foundational, widely-depended-on fact);
changes the activation-eligibility precondition logic; and touches the same
`select_for_update()`-guarded service already covered by Level 3 in Run 012. Repository-wide
grep confirmed no app outside `accounts`/`admin_portal`/`provider_portal`/`organization_portal`
references `ActivationEligibilityService`/`ProfileActivationService` directly, but the status
default change is upstream of `apps.orders`/`apps.accounts.services.supplier_bridge`
marketplace/financial-core eligibility reads, which the full suite exercises.

**Classification:** GREEN — all new/renamed tests pass, zero regressions in 1808 pre-existing
tests (two intentional, documented query-count baseline reductions), migration drift
unchanged from pre-task baseline (no new migration).

---

## Run 014 — Phase 2.1 Caregiver Professional Profile Foundation

```
Branch: phase2-caregiver-professional-profile-foundation (from main @ 0c9d70c)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.accounts.tests.test_caregiver_professional_profile` | 0 | 24/24 |
| `apps.provider_portal.tests.test_professional_profile` | 0 | 13/13 |
| `apps.public_site.tests.test_professional_profile_public` | 0 | 11/11 |
| `apps.accounts apps.provider_portal apps.public_site apps.orders apps.organization_portal apps.admin_portal` (Level 2 — directly affected apps) | 0 | 712/712 (incl. 1 locked query-count baseline update: provider_portal 9->12 — skills/experience counts + public-credential lookup, fixed-cost, not per-item) |
| `apps.kernel.tests.test_architecture_guardrails` (ServiceSupplierProfileCouplingTest) | 0 | 13/13 — confirms no new CaregiverProfile/OrganizationProfile import outside the documented allowlist |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged; confirmed no CaregiverSkill/CaregiverExperience/status-field entries present |
| **Full regression (Level 3 — model/migration changes, public/private security-boundary change on the caregiver public profile page, workflow spans accounts/provider_portal/public_site)** | **0** | **Ran 1874 tests — OK** (1824 baseline + 50 new) |

**Test level used:** Level 3 (full regression), run exactly once before PR creation,
justified by: two new models with a real migration (`CaregiverSkill`, `CaregiverExperience`);
a public/private security-boundary change on the caregiver public profile page (new local
eligibility check requiring `verification_status == VERIFIED` and account `is_active`); and
the workflow spans three apps (`accounts`, `provider_portal`, `public_site`) through shared
selectors (`PublicCredentialSelector`, `CaregiverPublicProfileService`).

**Classification:** GREEN — all 50 new/corrected tests pass, zero regressions in 1824
pre-existing tests (one intentional, documented query-count baseline increase; five
pre-existing public_site fixture calls corrected to `verification_status="verified"` — a
legitimate fix to fixtures that were unintentionally relying on lax eligibility, not a
workaround), migration drift unchanged from pre-task baseline beyond the two new,
intentional tables.

---

## Run 015 — Phase 2.1 Remediation: Close Public Caregiver Visibility Gap (BG-022)

```
Branch: phase2-caregiver-professional-profile-foundation (from main @ 0c9d70c)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.public_site.tests.test_public_visibility_policy` (new) | 0 | 13/13 |
| `apps.public_site.tests.{test_directory_service,test_home_service,test_profile_service,test_views,test_professional_profile_public,test_organization_profile_service}` | 0 | 92/92 |
| `apps.public_site apps.provider_portal apps.accounts` (Level 2 — directly affected) | 0 | 491/491 |
| `apps.discovery apps.orders` (Level 2 — selector consumers of the touched supplier_bridge helper) | 0 | 169/169 |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged; no model changes in this remediation |
| **Full regression (Level 3 — public/private security-boundary change on shared public selectors, spans accounts/public_site)** | **0** | **Ran 1887 tests — OK** (1874 baseline + 13 new) |

**Test level used:** Level 3 (full regression), run exactly once before updating PR #6,
justified by: this remediation changes a public/private security boundary shared across
multiple selectors (`apps.public_site.services.common`) and reaches into `apps.accounts`
(`supplier_bridge.py`) — exactly the "shared public selectors" Level-3 trigger.

**Classification:** GREEN — all 13 new tests pass, zero regressions in 1874 pre-existing
tests (one intentional query-count reduction in an existing test — removing the detail
page's now-redundant duplicate check saved one query — and one fixture-default correction
in `apps/public_site/tests/helpers.py`, confirmed safe by grep showing no pre-existing
test asserted on the old default), migration drift unchanged from pre-task baseline (no
new migration). A pre-existing, unrelated per-candidate query cost in directory ranking/
card-building was discovered and recorded (KL-012), not fixed (out of scope).

---

## Run 016 — Sprint 2.2: Caregiver Gallery and Media Portfolio

```
Branch: phase2-caregiver-gallery-media (from main @ c5259b3, PR #6 merged)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.accounts.tests.test_caregiver_gallery` (new) | 0 | 21/21 |
| `apps.provider_portal.tests.test_gallery` (new) | 0 | 13/13 |
| `apps.public_site.tests.test_gallery_public` (new) | 0 | 11/11 |
| `apps.accounts apps.provider_portal apps.public_site` (Level 2 — directly affected) | 0 | 536/536 |
| `apps.kernel.tests.test_architecture_guardrails` | 0 | 13/13 |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged; the new `accounts/0007_caregiver_gallery_item.py` migration is fully applied/detected, no residual drift from it |
| **Full regression (Level 3 — new model + migration, file-upload/privacy boundary, public profile change, spans accounts/provider_portal/public_site)** | **0** | **Ran 1932 tests — OK** (1887 baseline + 45 new) |

**Test level used:** Level 3 (full regression), run exactly once before creating the
Sprint 2.2 PR, justified by: a new model and migration, a file-upload/privacy boundary
(gallery image validation and ownership), a public-profile change, and several apps
(accounts, provider_portal, public_site) — exactly this repository's own stated Level-3
trigger set.

**Classification:** GREEN — all 45 new tests pass, zero regressions in 1887 pre-existing
tests (two intentional, documented query-count bumps: the provider profile page's own
locked baseline moved 12 -> 13 for the new `gallery_count` query, and the public profile
page's locked baseline moved 13 -> 14 for the new `_gallery()` query — both are fixed,
O(1) costs, proven by dedicated query-count tests in the new test files, not per-item
N+1s), migration drift unchanged from pre-task baseline beyond the one new, intentional
table.

---

## Run 017 — PR #7 Remediation: Harden Gallery File Lifecycle and Image Safety

```
Branch: phase2-caregiver-gallery-media (from main @ c5259b3, PR #6 merged)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.accounts.tests.test_caregiver_gallery` (16 new + 21 existing, updated) | 0 | 37/37 |
| `apps.accounts apps.provider_portal apps.public_site` (Level 2 — directly affected) | 0 | 552/552 |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged; no model change in this remediation |
| **Full regression (Level 3 — shared image validator and public file lifecycle are security boundaries across multiple surfaces)** | **0** | **Ran 1948 tests — OK** (1932 baseline + 16 new) |

**Test level used:** Level 3 (full regression), run exactly once before updating PR #7,
justified by: the shared `image_validation.validate_image()` function and the gallery's
public file lifecycle are both security/data-integrity boundaries reached from multiple
surfaces (avatar/cover upload, gallery upload, the public profile page) — exactly this
remediation's own stated Level-3 trigger.

**Note on test infrastructure:** proving "rollback discards a scheduled physical deletion"
and "a storage-deletion failure does not raise or restore the row" required
`transaction.on_commit()`-aware assertions. `TransactionTestCase` (this repo's usual tool
for real-commit semantics) was tried first and found to trip a pre-existing, unrelated
Postgres/Django flush-teardown incompatibility in this environment — reproduced with a
minimal fixture-only `TransactionTestCase` that does nothing but create a `UserAccount`
row, confirmed unrelated to this remediation, and explicitly out of this narrowly-scoped
remediation's mandate to fix. Used `django.test.TestCase.captureOnCommitCallbacks()`
instead, which correctly reflects Django's real nested-atomic-rollback discard behavior
(verified directly before relying on it) without requiring the outermost per-test
transaction to ever truly commit.

**Classification:** GREEN — all 16 new tests pass (7 file-lifecycle safety + 9 image-safety
limit tests, one of which — a genuine `PIL.Image.DecompressionBombError`, not simulated —
is triggered by patching Pillow's own global threshold down, not by mocking the exception
itself), zero regressions in 1932 pre-existing tests, migration drift unchanged from
pre-task baseline (no new migration).

---

## Run 018 — Sprint 2.3: Credentials, Skills, Experience, Highlights

```
Branch: phase2-caregiver-credentials-skills-experience-ui (from main @ f7b7b2b, PR #7 merged)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.accounts.tests.{test_caregiver_professional_profile,test_verification_policy}` | 0 | 51/51 |
| `apps.provider_portal.tests.test_professional_profile` | 0 | 24/24 |
| `apps.public_site.tests.test_professional_profile_public` | 0 | 22/22 |
| `apps.accounts apps.provider_portal apps.public_site` (Level 2 — directly affected) | 0 | 588/588 |
| `apps.organization_portal` (shared verification_badge.html blast-radius check) | 0 | 51/51 |
| `apps.kernel.tests.test_architecture_guardrails` | 0 | 13/13 |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged; no model change this sprint |
| **Full regression (Level 3 — public credential presentation changes across several apps, per this sprint's own explicit Level-3 trigger)** | **0** | **Ran 1984 tests — OK** (1948 baseline + 36 new) |

**Test level used:** Level 3 (full regression), run exactly once before creating the
Sprint 2.3 PR, justified by: shared selector/ViewModel changes
(`PublicCredentialViewModel`, `CaregiverProfileViewModel`), a public/private presentation
boundary change (precise badges, highlights), and a shared UI component
(`verification_badge.html`) reaching into `apps.organization_portal` as well as
`apps.provider_portal` — exactly the sprint's own stated Level-3 trigger set.

**Classification:** GREEN — all 36 new tests pass, zero regressions in 1948 pre-existing
tests (one intentional, documented query-count bump: the provider profile page's own
locked baseline moved 13 -> 15 for the two new visible-skill/visible-experience count
queries the owner-side highlights preview needs — proven fixed-cost, not per-item, by the
unchanged test structure; the public profile page's own query count stayed at 14,
confirming the public highlights/badges add zero new queries as designed), migration
drift unchanged from pre-task baseline (no new migration).

## Run 019 — Sprint 2.4: Caregiver Availability and Working Schedule

```
Branch: phase2-caregiver-availability-schedule (from main @ 20c532e, PR #8 merged)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.availability.tests` (mutation + query service, full app suite) | 0 | 56/56 |
| `apps.provider_portal.tests.test_availability_views` | 0 | 21/21 |
| `apps.public_site.tests.test_professional_profile_public` (schedule summary class) | 0 | 6/6 |
| `apps.availability apps.provider_portal apps.public_site` (Level 2 — directly affected) | 0 | 297/297 |
| `apps.booking` (proactive extra check — existing is_supplier_available() consumer) | 0 | 67/67 |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only (kernel.ServiceSupplier/UserAccount fields); confirmed identical on merged main before this sprint's changes via git stash comparison; no availability-app drift |
| **Full regression (Level 3 — new cross-app edge apps.public_site -> apps.availability, public/private boundary change via schedule summary, multiple apps affected)** | **0** | **Ran 2024 tests — OK** (1984 baseline + 40 new) |

**Test level used:** Level 3 (full regression), run exactly once before creating the
Sprint 2.4 PR, justified by: a new documented cross-app dependency edge
(`apps.public_site` -> `apps.availability`), a public/private presentation boundary change
(the new schedule summary section), and three apps affected directly
(`apps.availability`, `apps.provider_portal`, `apps.public_site`) plus one proactive
consumer check (`apps.booking`) — matching this sprint's own Level-3 trigger set.

**Classification:** GREEN — all 40 new tests pass, zero regressions in 1984 pre-existing
tests (two intentional, documented query-count bumps: both public-profile locked
baselines — `PublicProfileQueryCountTest` and `PublicGalleryQueryCountTest` — moved
14 -> 15 for the one new fixed-cost `get_distinct_active_days()` query the schedule
summary needs, proven O(1) by the existing gallery-item-count scaling structure; the new
provider-portal availability-page query count was newly locked at 9, no prior baseline
existed to compare against), migration drift unchanged from pre-task baseline (no new
migration, confirmed identical to merged main via git stash comparison).

## Run 020 — PR #9 Review Remediation: Availability Mutation Concurrency

```
Branch: phase2-caregiver-availability-schedule (from main @ 20c532e, PR #8 merged;
  PR #9 open, not yet merged)
Settings module: config.settings.testing
Python: 3.11.15  |  Django: 5.2.16  |  PostgreSQL: 16.13
Date/time: 2026-07-15
```

| Command | Exit code | Result |
|---------|-----------|--------|
| `python manage.py check` | 0 | System check identified no issues |
| `apps.availability.tests.test_concurrency` (new, focused) | 0 | 9/9 |
| `apps.availability` (full app suite, includes the 9 new concurrency tests) | 0 | 65/65 |
| `apps.provider_portal` (full app suite) | 0 | 107/107 |
| `python manage.py makemigrations --check --dry-run` | 1 | Pre-existing cosmetic drift only, unchanged; no schema change this remediation |
| **Full regression (production locking/mutation code changed)** | **0** | **Ran 2033 tests — OK** (2024 baseline + 9 new) |

**Test level used:** Full regression, run exactly once, per this remediation's own explicit
policy ("if production locking or mutation code changes, run the full repository suite
exactly once before updating PR #9") — `AvailabilityMutationService` (production mutation
code) was modified. `apps.booking` was not re-run: `AvailabilityQueryService`/
`is_supplier_available()` (booking's own dependency) were not touched by this remediation,
and the remediation's own test policy only requires a booking re-run "if shared evaluator
behavior is modified."

**Classification:** GREEN — all 9 new concurrency tests pass against real, separately-
committed transactions (`TransactionTestCase`, not `TestCase`), each asserting final
database state rather than only the raised/absent exception. Zero regressions in the 2024
pre-existing tests. Zero new migration — `makemigrations --check --dry-run` drift
unchanged from the pre-remediation baseline (only the pre-existing, unrelated
`kernel.ServiceSupplier`/`UserAccount` field drift).
