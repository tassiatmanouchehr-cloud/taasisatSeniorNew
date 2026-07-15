# CHANGE LEDGER

**Repository:** taasisatSenior
**Branch:** main
**Policy:** Append-only. Each entry is a permanent record of one change.

---

## Entry 001

```
Change ID: CL-001
Date/time: 2026-07-13T16:49:00Z
Task: Create REPORT_1_CURRENT_SYSTEM_FORENSIC_ANALYSIS.md
Reason: Architecture authority requested comprehensive code-only analysis of entire codebase
Files added: REPORT_1_CURRENT_SYSTEM_FORENSIC_ANALYSIS.md
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (analysis only)
Result: Success — 20-section report covering all 65 models, 78+ services, 120+ views, 12 API endpoints
Rollback method: Delete the file
Status: Permanent
```

## Entry 002

```
Change ID: CL-002
Date/time: 2026-07-13T17:15:00Z
Task: Create REPORT_2_COMPLETION_ASSESSMENT.md
Reason: Architecture authority requested evidence-based completion status for every subsystem
Files added: REPORT_2_COMPLETION_ASSESSMENT.md
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: 1632 (full suite), 18 (E2E workflow)
Result: Success — 20-section assessment with 75 subsystem classifications
Rollback method: Delete the file
Status: Permanent
```

## Entry 003

```
Change ID: CL-003
Date/time: 2026-07-13T17:30:00Z
Task: Create src/e2e_validation.py, src/fix_perms.py, src/setup_db.py
Reason: Required scripts for E2E workflow execution against PostgreSQL
Files added: src/e2e_validation.py, src/fix_perms.py, src/setup_db.py
Files modified: None
Files deleted: None
Database impact: Created test data in marketplace database (users, profiles, orders, etc.)
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: E2E workflow (18 steps)
Result: Success — all 18 E2E steps passed
Rollback method: Delete scripts, truncate test data
Status: Temporary (should be cleaned up)
```

## Entry 004

```
Change ID: CL-004
Date/time: 2026-07-13T18:00:00Z
Task: Create MARKETPLACE_GOLDEN_FLOW_GAP_REPORT.md
Reason: Architecture authority requested gap analysis between current E2E flow and required marketplace golden flow
Files added: MARKETPLACE_GOLDEN_FLOW_GAP_REPORT.md
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (analysis only)
Result: Success — 14-step gap analysis with dependency graph
Rollback method: Delete the file
Status: Permanent
```

## Entry 005

```
Change ID: CL-005
Date/time: 2026-07-13T18:30:00Z
Task: Create OFFER_MARKETPLACE_CONTRACT.md (first draft)
Reason: Architecture authority requested implementation contract for Offer Marketplace epic
Files added: OFFER_MARKETPLACE_CONTRACT.md
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (design only)
Result: Success — initial contract with 10 sections
Rollback method: Delete the file
Status: Superseded by revised contract
```

## Entry 006

```
Change ID: CL-006
Date/time: 2026-07-13T19:00:00Z
Task: Create OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md (revised)
Reason: Architecture authority identified 12 issues in first draft requiring correction
Files added: OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (design only)
Result: Success — revised contract addressing all 12 issues
Rollback method: Delete the file
Status: Active (under final remediation)
```

## Entry 007

```
Change ID: CL-007
Date/time: 2026-07-13T20:00:00Z
Task: Create mimo change/ directory and begin retrospective documentation
Reason: Architecture authority granted conditional approval; requested final documentation phase
Files added: mimo change/00_WORK_COMPLETED_TO_DATE.md, mimo change/01_CHANGE_LEDGER.md, mimo change/02_ARCHITECTURE_DECISION_LOG.md
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (documentation only)
Result: Interrupted after creating 3 of 9 planned files
Rollback method: Delete mimo change/ directory
Status: Interrupted — resumed in CL-008
```

## Entry 008

```
Change ID: CL-008
Date/time: 2026-07-13T21:00:00Z
Task: Resume and complete final documentation and contract remediation
Reason: Architecture authority granted conditional approval; task resumed after interruption
Files added: mimo change/03_FILE_CHANGE_REGISTER.md, mimo change/04_TEST_EXECUTION_LOG.md, mimo change/05_OPEN_QUESTIONS_AND_RISKS.md, mimo change/06_FINAL_CONTRACT_REMEDIATION_REPORT.md, mimo change/07_CONTRACT_DIFF_SUMMARY.md, mimo change/08_FINAL_TASK_VERIFICATION.md
Files modified: OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md (three remediations: visibility guard, deadline reuse, REJECTED semantics), mimo change/00_WORK_COMPLETED_TO_DATE.md (corrections: working-tree status, E2E history, integrity statement), mimo change/01_CHANGE_LEDGER.md (corrected CL-007), mimo change/02_ARCHITECTURE_DECISION_LOG.md (ADM-011 status)
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (documentation only)
Result: Success — all 9 documentation files created, contract remediated, consistency audit passed
Rollback method: Delete mimo change/ directory, restore contract from git
Status: Complete
```

## Entry 009

```
Change ID: CL-009
Date/time: 2026-07-13T22:00:00Z
Task: Final documentation consistency correction — remove obsolete job references, normalize risk statuses, resolve RISK-004 payment retry linkage
Reason: Architecture authority requested final corrections before implementation approval
Files added: None
Files modified: OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md (removed jobs.py from planned files, added Section 6A for PaymentIntent FK, updated confirm_payment signature, added payments/models.py to modified files), mimo change/02_ARCHITECTURE_DECISION_LOG.md (added ADM-012), mimo change/03_FILE_CHANGE_REGISTER.md (removed jobs.py, added payments/models.py), mimo change/05_OPEN_QUESTIONS_AND_RISKS.md (normalized all risk statuses), mimo change/06_FINAL_CONTRACT_REMEDIATION_REPORT.md (added RISK-004 resolution, normalized statuses), mimo change/07_CONTRACT_DIFF_SUMMARY.md (added RISK-004 diff), mimo change/08_FINAL_TASK_VERIFICATION.md (updated remediation count)
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (documentation only)
Result: Success — obsolete references removed, risk statuses normalized, RISK-004 resolved in contract
Rollback method: Restore files from previous state
Status: Complete
```

## Entry 010

```
Change ID: CL-010
Date/time: 2026-07-13T23:00:00Z
Task: Phase 1 Implementation — OrderOffer Model Domain Foundation
Reason: Architecture authority approved implementation; Phase 1 scope: model, migration, admin, tests
Files added: src/apps/orders/migrations/0008_orderoffer.py, src/apps/orders/tests/test_order_offer_model.py, src/cleanup_test_db.py, mimo change/09_IMPLEMENTATION_JOURNAL.md
Files modified: src/apps/orders/models.py (added OrderOfferStatus, OFFER_TERMINAL_STATUSES, OrderOffer), src/apps/orders/admin.py (added OrderOfferAdmin)
Files deleted: src/apps/kernel/migrations/0012_orderoffer.py (phantom migration due to Django version drift)
Database impact: New table orders_order_offer with 2 conditional UniqueConstraints and 2 composite indexes
Migration impact: orders.0008_orderoffer.py created; kernel.0012_orderoffer.py deleted (phantom)
Security impact: None — model is add-only, no auth changes
Financial impact: None — price_amount/currency fields only, no financial operations
Tests executed: 24 new OrderOffer model tests + 1632 existing tests = 1656 total
Result: Success — 1656/1656 tests passed, 0 failures
Rollback method: Delete 0008_orderoffer.py migration, revert models.py and admin.py changes
Status: Complete
```

## Entry 011

```
Change ID: CL-011
Date/time: 2026-07-14T00:00:00Z
Task: Phase 1 Remediation — OrderOffer domain foundation corrections
Reason: Architecture review identified 5 issues: premature PaymentIntent reference, active-only uniqueness policy, temporary cleanup tooling, incomplete properties, documentation inconsistencies
Files added: src/apps/orders/migrations/0009_orderoffer_canonical.py
Files modified: src/apps/orders/models.py (removed PaymentIntent docstring, changed to canonical uniqueness constraint, updated status comments), src/apps/orders/tests/test_order_offer_model.py (updated 4 tests for canonical constraint, added 1 new test)
Files deleted: src/cleanup_test_db.py, src/apps/kernel/migrations/0012_orderoffer_canonical.py (phantom)
Database impact: Constraint changed from conditional (submitted|selected) to unconditional (order, supplier)
Migration impact: orders.0009_orderoffer_canonical.py replaces conditional constraint with canonical constraint; kernel.0012 deleted (phantom)
Security impact: None
Financial impact: None
Tests executed: 25 new OrderOffer model tests + 1632 existing tests = 1657 total
Result: Success — 1657/1657 tests passed, 0 failures
Rollback method: Revert 0009 migration, restore conditional constraint in models.py
Status: Complete
```

## Entry 012

```
Change ID: CL-012
Date/time: 2026-07-14T01:00:00Z
Task: Phase 1 Completion Remediation — Squash migration, add domain properties, clean tests, clean admin
Reason: Architecture review identified incomplete remediation: two migrations instead of one, missing domain properties, test quality issues
Files added: None
Files modified: src/apps/orders/migrations/0008_orderoffer.py (squashed: canonical constraint now in initial migration), src/apps/orders/models.py (added can_edit, can_withdraw, can_select properties), src/apps/orders/tests/test_order_offer_model.py (rewritten uniqueness tests, added 9 domain property tests, 40 total)
Files deleted: src/apps/orders/migrations/0009_orderoffer_canonical.py (squashed into 0008)
Database impact: Single migration with unconditional (order, supplier) constraint + conditional one-selected-per-order constraint
Migration impact: orders.0008_orderoffer.py now contains final schema; 0009 deleted
Security impact: None
Financial impact: None
Tests executed: 40 OrderOffer model tests + 1632 existing tests = 1672 total
Result: Success — 1672/1672 tests passed, 0 failures
Rollback method: Revert 0008 migration to original conditional constraint
Status: Complete
```

## Entry 013

```
Change ID: CL-013
Date/time: 2026-07-14T02:00:00Z
Task: Phase 1 Traceability and Test Evidence — Documentation and exit-code capture
Reason: Complete all mandatory traceability documentation and record real Python/Django process exit codes
Files added: None
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: manage.py check (exit 0), makemigrations --check (exit 1, cosmetic drift), OrderOffer targeted (exit 0, 40/40), Orders full (exit 0, 119/119), Full regression (exit 1, 1671/1672 — 1 pre-existing seed test error)
Result: Documentation updated, exit codes recorded, pre-existing seed test error documented
Rollback method: N/A (documentation only)
Status: Complete
```

## Entry 014

```
Change ID: CL-014
Date/time: 2026-07-14T03:00:00Z
Task: Create permanent repository memory (PROJECT_CONTINUATION.md, NEXT_TASK.md)
Reason: Ensure any future AI assistant can continue the project correctly with zero conversation memory
Files added: PROJECT_CONTINUATION.md, NEXT_TASK.md
Files modified: None
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (documentation only)
Result: Two repository-level continuation files created, traceability updated
Rollback method: Delete the two files
Status: Complete
```

## Entry 015

```
Change ID: CL-015
Date/time: 2026-07-14T11:54:00Z
Task: Complete repository forensic audit and canonical documentation suite creation
Reason: Architecture authority requested comprehensive evidence-based analysis of entire repository and consolidation into canonical documentation suite
Files added: canonical docs/00_CANONICAL_INDEX.md through 19_EVIDENCE_AND_METHOD.md (19 files), mimo change/audit/00_AUDIT_EXECUTIVE_SUMMARY.md through 11_UNRESOLVED_QUESTIONS.md (12 files)
Files modified: mimo change/01_CHANGE_LEDGER.md (this entry)
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: None (documentation only)
Result: 19 canonical documents + 12 audit reports created. Root PROJECT_CONTINUATION.md and NEXT_TASK.md updated. Evidence-based findings: 2 CRITICAL, 4 HIGH, 4 MEDIUM, 3 LOW. 14-item prioritized backlog.
Rollback method: Delete canonical docs/ directory and mimo change/audit/ directory
Status: Complete
```

## Entry 016

```
Change ID: CL-016
Date/time: 2026-07-14 (documentation sync task)
Task: Documentation synchronization with HEAD ce3b30e + executable current-HEAD verification
Reason: Verification found material drift: OrderOffer Phase 1 was committed in ce3b30e but active docs still described it as uncommitted working-tree state; root docs and registry referenced obsolete paths (canonical docs/, mimo change/, docs/architecture/) that were archived by ce3b30e's reorganization
Files added: None (project docs/IMPLEMENTATION_ROADMAP.md added previously in ed33e47)
Files modified:
  README.md (documentation section now points to project docs/00_START_HERE.md; removed archived docs/architecture links)
  AI_START_HERE.md (short entry point to project docs/)
  DOCUMENTATION_RULES.md (points only to project docs/)
  PROJECT_CONTINUATION.md (reduced to pointer to project docs/02_PROJECT_CONTINUATION.md)
  NEXT_TASK.md (reduced to pointer to project docs/03_NEXT_TASK.md)
  project docs/00_START_HERE.md (roadmap added to reading order and directory roles)
  project docs/01_PROJECT_RULES.md (paths updated to project docs/)
  project docs/DOCUMENTATION_RULES.md (paths updated to project docs/)
  project docs/02_PROJECT_CONTINUATION.md (HEAD ce3b30e, Phase 1 committed, clean tree, repo name taasisatSeniorNew, active-doc paths)
  project docs/03_NEXT_TASK.md (BG-001 marked done; next task = roadmap Phase 1 Registration & Verification, pending approval)
  project docs/current/IMPLEMENTATION_STATE.md (HEAD, orders row, offer marketplace section: committed + migrate verified)
  project docs/current/SYSTEM_OVERVIEW.md (HEAD, maturity row, traceability path)
  project docs/quality/COMPLETION_BACKLOG.md (BG-001 COMPLETE; BG-002 re-characterized as random in-run collision with 2026-07-14 evidence)
  project docs/quality/LEGACY_AND_DEAD_CODE.md (HEAD; migration table: 0008 committed; makemigrations drift note)
  project docs/audit/DOCUMENTATION_CONTRADICTIONS.md (appended resolution update)
  project docs/registry/DOCUMENTATION_REGISTRY.md (active list rewritten to project docs/ paths; roadmap registered)
  project docs/registry/SUPERSESSION_MAP.md (governing rule and superseded paths updated)
  project docs/IMPLEMENTATION_ROADMAP.md (verification row updated with executed evidence; G12 re-characterized)
  project docs/traceability/TEST_EXECUTION_LOG.md (Run 008 appended)
  project docs/traceability/FILE_CHANGE_REGISTER.md (this sync appended)
Files deleted: None
Database impact: None (verification only; test databases auto-created/destroyed)
Migration impact: None (no migration files changed; migrate verified clean at ce3b30e)
Security impact: None
Financial impact: None
Tests executed: check (exit 0), makemigrations --check (exit 1, pre-existing cosmetic drift), migrate (exit 0), seed test x10 isolated (9 pass / 1 fail — random in-run order_number collision), full suite (exit 1, 1662 ran, 2 errors, both the pre-existing seed collision)
Result: Documentation synchronized with repository; HEAD ce3b30e classified GREEN_EXCEPT_CONFIRMED_PRE_EXISTING_FLAKY_TEST
Rollback method: git checkout of the modified documentation files
Status: Complete — committed to working branch claude/taasisat-senior-state-verify-9dzzlm (persistence required by repository stop hook; ephemeral environment). Merge to main still awaits owner approval.
```

## Entry 017

```
Change ID: CL-017
Date/time: 2026-07-14 (BG-002 fix task)
Task: Fix BG-002 — order_number random collision in Order auto-generation
Reason: Confirmed pre-existing flaky defect: _generate_order_number() used a 4-digit random daily suffix (10,000/day) against a globally unique column; the seed walkthrough collided randomly in isolation (1/10) and in full regression (2 test classes at ce3b30e)
Root cause: In-run birthday-problem collision; generation was not collision-safe and a rejected insert aborted the caller's transaction
Chosen fix: Option D — bounded retry + stronger entropy. Order.save() retries auto-generation up to ORDER_NUMBER_MAX_ATTEMPTS=5 on the order_number unique violation, each attempt in its own savepoint (transaction.atomic) so caller @transaction.atomic blocks are not poisoned; caller-supplied duplicates and other IntegrityErrors raise immediately; suffix widened 4→6 digits (format family ORD-YYYYMMDD-NNNNNN preserved, 19 chars ≤ max_length 30). DB unique constraint remains the sole arbiter (no check-then-insert)
Alternatives rejected: retry-only (10k/day ceiling), entropy-only (defect class survives), DB sequence (format change, volume leak, exceeds minimal scope), timestamp component (concurrent same-instant collision, prohibited by task)
Files added: src/apps/orders/tests/test_order_number_generation.py (8 regression tests: format ×2, forced-collision retry, no-overwrite, bounded retry, explicit-duplicate passthrough, savepoint non-poisoning, TransactionTestCase concurrency)
Files modified: src/apps/orders/models.py (generator + save retry), project docs/02_PROJECT_CONTINUATION.md, project docs/03_NEXT_TASK.md, project docs/quality/COMPLETION_BACKLOG.md (BG-002 COMPLETE), project docs/quality/DEFECT_AND_RISK_REGISTER.md (FR-005 RESOLVED), project docs/traceability/* (appends)
Files deleted: None
Database impact: None (no schema change; existing 4-digit order numbers remain valid)
Migration impact: NONE — makemigrations --check output unchanged (pre-existing cosmetic drift only, zero orders entries)
Security impact: None
Financial impact: None
Tests executed: check exit 0; makemigrations --check exit 1 (pre-existing, unchanged); new regression tests 8/8 exit 0; seed walkthrough suite 46 tests exit 0; orders suite 127 tests exit 0; previously flaky isolated test 20/20 exit 0; FULL REGRESSION exit 0 — Ran 1680 tests, OK
Result: BG-002 resolved; first fully green full regression on record
Rollback method: git revert of the fix commit; no data cleanup required
Status: Complete
```

## Entry 018

```
Change ID: CL-018
Date/time: 2026-07-14 (post-merge documentation sync)
Task: Synchronize active documentation with merged main after PR #1
Reason: PR #1 ("Synchronize active documentation and fix order-number collisions") merged into main as eb51018ffbc9faeebae08adebcc21d6dbfe7b92e; HEAD/status metadata in active docs became outdated
Files added: None
Files modified:
  project docs/02_PROJECT_CONTINUATION.md (main HEAD eb51018; BG-002 merged; Phase 1 ACTIVE; work branch restarted from main)
  project docs/03_NEXT_TASK.md (BG-002 merged; Phase 1 marked ACTIVE, implementation not started)
  project docs/IMPLEMENTATION_ROADMAP.md (post-merge header; P0 hygiene + G12 marked done/merged)
  project docs/quality/COMPLETION_BACKLOG.md (BG-002 merge record)
  project docs/current/IMPLEMENTATION_STATE.md (HEAD eb51018; orders 167 tests; total 1,680)
  project docs/current/SYSTEM_OVERVIEW.md (HEAD eb51018)
  project docs/traceability/CHANGE_LEDGER.md (this entry)
  project docs/traceability/FILE_CHANGE_REGISTER.md (append)
  project docs/traceability/IMPLEMENTATION_JOURNAL.md (merge record append)
Files deleted: None
Database impact: None
Migration impact: None
Security impact: None
Financial impact: None
Tests executed: git status --short (clean before doc edits), git log -1 (eb51018 merge commit), manage.py check (exit recorded in this task's report)
Result: Active documentation synchronized with merged main; Phase 1 — Registration and Verification Workflows is the active implementation phase (not yet started)
Rollback method: git checkout of the modified documentation files
Status: Complete
```

## Entry 019

```
Change ID: CL-019
Date/time: 2026-07-15 (Phase 1.1 — Registration and Manual Verification Foundation)
Task: Implement manual document verification workflow for caregiver/organization VerificationDocument
Reason: Registration flows verified defect-free (Part A); root missing workflow was the
        platform-admin document review path both apps/accounts/models/media.py and
        apps/accounts/services/document_service.py explicitly named as future/out-of-scope
Files added:
  src/apps/accounts/migrations/0005_add_correction_required_document_status.py
  src/apps/accounts/services/verification_review_service.py
  src/apps/accounts/services/verification_evaluator.py
  src/apps/accounts/tests/test_verification_review.py
  src/apps/admin_portal/tests/test_document_verification.py
  src/templates/admin_portal/document_verification_queue.html
  src/templates/admin_portal/document_verification_detail.html
Files modified:
  src/apps/accounts/models/media.py (DocumentStatus.CORRECTION_REQUIRED; rejection_reason
    and module docstrings updated — see ARCHITECTURE_DECISION_LOG ADM-014)
  src/apps/kernel/permissions/keys.py (ACCOUNTS_DOCUMENT_REVIEW registered)
  src/apps/accounts/permission_keys.py (re-export)
  src/apps/admin_portal/permission_keys.py (re-export as DOCUMENT_REVIEW)
  src/apps/kernel/role_catalog.py (granted to platform_owner/platform_admin/platform_support)
  src/apps/admin_portal/forms.py (DocumentReviewForm)
  src/apps/admin_portal/views.py (4 new views: queue, detail, file, review action)
  src/apps/admin_portal/urls.py (4 new routes under /admin-portal/verification/documents/)
  src/templates/admin_portal/home.html (nav card)
  src/ui/components/portal/verification_badge.html (correction_required branch)
  src/ui/components/portal/document_status.html (docstring: action_message now owner-visible reason)
  src/templates/provider_portal/document_upload.html (action_message wired to rejection_reason)
  src/templates/organization_portal/document_upload.html (same)
Files deleted: None
Database impact: VerificationDocument.status choices gains CORRECTION_REQUIRED (no schema/constraint change)
Migration impact: accounts.0005 — AlterField choices only, hand-trimmed to exclude pre-existing
  unrelated cosmetic drift the same makemigrations run also detected (bio/caregiver_note/
  organization/reviewer_note/notes/address/code/description — untouched, out of scope)
Security impact: New accounts.document.review permission key, tenant re-derived from document
  owner and compared before permission check (cross-tenant lookups indistinguishable from
  not-found), self-review refused as defense-in-depth independent of RBAC grants
Financial impact: None
Tests executed: check (0), makemigrations --check (1, pre-existing unrelated drift only),
  migrate (0), new service tests 25/25, new view tests 16/16, accounts suite 205/205,
  admin_portal suite 45/45, kernel suite 232/232, provider_portal+organization_portal+
  public_site 182/182, existing registration tests 8/8, full regression 1721/1721 (exit 0)
Result: Success — manual document verification workflow implemented for caregiver and
  organization documents; customer verification and profile roll-up explicitly deferred
  (no domain-model support / no required-document policy respectively — see journal)
Rollback method: git revert of the branch's commits; migration 0005 reverses cleanly
  (AlterField back to 3 choices) with no data loss since CORRECTION_REQUIRED rows would
  need manual reclassification only if any existed at rollback time
Status: Complete — branch phase1-registration-manual-verification, PR to be created, NOT merged
```

## Entry 020

```
Change ID: CL-020
Date/time: 2026-07-15 (Phase 1.2 — Verification Completion and Activation Rules)
Task: Implement required-document policy, profile verification roll-up, correction/
      resubmission lifecycle, and read-only activation eligibility
Reason: Closes the two items Phase 1.1 explicitly deferred (BG-016 remains deferred;
        BG-017 required-document policy + roll-up now implemented) per the roadmap's
        Phase 1 acceptance criterion 3
Files added:
  src/apps/accounts/services/document_ownership.py
  src/apps/accounts/services/verification_policy.py
  src/apps/accounts/services/verification_rollup_service.py
  src/apps/accounts/services/activation_eligibility_service.py
  src/apps/accounts/tests/test_verification_policy.py
  src/apps/accounts/tests/test_verification_rollup.py
  src/apps/accounts/tests/test_document_resubmission.py
  src/apps/accounts/tests/test_activation_eligibility.py
Files modified:
  src/apps/accounts/services/document_service.py (resubmit() added; class/module docstrings updated)
  src/apps/accounts/services/profiles.py (calculate_organization_profile_completion() added)
  src/apps/accounts/services/verification_review_service.py (delegates tenant/owner
    resolution to document_ownership.py; calls ProfileVerificationRollupService.sync_*
    at the end of _apply_review, same transaction)
  src/apps/provider_portal/views.py (document_manage_view calls DocumentService.resubmit()
    instead of replace_document() directly)
  src/apps/organization_portal/views.py (same)
Files deleted: None
Database impact: None
Migration impact: None — pure service-layer addition; verified via makemigrations --check
  showing identical pre-existing drift only (no new accounts/kernel entries)
Security impact: No new permission key (resubmission is an ownership check, mirrors
  get_owned_document()'s existing shape, not RBAC-gated); cross-tenant/cross-owner
  resubmission denied via shared document_ownership helpers; VERIFIED documents can no
  longer be silently replaced by their owner (see ARCHITECTURE_DECISION_LOG ADM-015)
Financial impact: None
Tests executed: check (0), makemigrations --check (1, pre-existing unrelated drift only),
  47 new tests across 4 files (all 0), existing test_verification_review.py 25/25 (no
  regression from rollup-sync wiring), accounts suite 252/252, provider_portal +
  organization_portal suite 102/102, full regression 1768/1768 (exit 0)
Result: Success — required-document policy, profile roll-up, resubmission lifecycle, and
  activation eligibility all implemented; zero regressions; zero migrations
Rollback method: git revert of the branch's commit(s); no data migration to reverse
Status: Complete — branch phase1-verification-activation-rules, PR to be created, NOT merged
```

## Entry 021

```
Change ID: CL-021
Date/time: 2026-07-15 (Phase 1.3 — Complete Phase 1 Activation and Profile Completion)
Task: Deterministic profile completion (Part A), controlled caregiver/organization
      activation wired to ActivationEligibilityService (Part B/C), minimum usable
      platform-operator and owner-facing activation UI (Part D)
Reason: Closes the two remaining Phase 1 items: wiring ActivationEligibilityService into
        a real controlled activation action, and making profile completion deterministic
        and single-source-of-truth (BG-018) — completing roadmap Phase 1 acceptance
        criteria per project docs/IMPLEMENTATION_ROADMAP.md
Files added:
  src/apps/accounts/services/profile_completion_service.py
  src/apps/accounts/services/profile_activation_service.py
  src/apps/accounts/tests/test_profile_completion.py
  src/apps/accounts/tests/test_profile_activation.py
  src/apps/admin_portal/tests/test_profile_activation.py
  src/apps/provider_portal/tests/test_activation_presentation.py
  src/apps/organization_portal/tests/test_activation_presentation.py
  src/templates/admin_portal/caregiver_activation_detail.html
  src/templates/admin_portal/organization_activation_detail.html
  src/ui/components/portal/activation_status.html
Files modified:
  src/apps/accounts/services/profiles.py (completion percentage delegated to
    ProfileCompletionService; bare-int signatures unchanged)
  src/apps/kernel/permissions/keys.py (ACCOUNTS_PROFILE_ACTIVATE registered)
  src/apps/accounts/permission_keys.py (re-export)
  src/apps/admin_portal/permission_keys.py (re-export as PROFILE_ACTIVATE)
  src/apps/kernel/role_catalog.py (DOCUMENT_REVIEW_PERMISSIONS renamed
    PLATFORM_VERIFICATION_PERMISSIONS, now includes ACCOUNTS_PROFILE_ACTIVATE, granted to
    platform_owner/platform_admin/platform_support)
  src/apps/admin_portal/views.py (4 new views: caregiver/organization activation
    detail + activate action)
  src/apps/admin_portal/urls.py (4 new routes)
  src/templates/admin_portal/document_verification_queue.html (owner name links to new
    activation detail page)
  src/templates/admin_portal/document_verification_detail.html (same, on the owner row)
  src/apps/provider_portal/services/viewmodels.py (is_activated/activation_eligible/
    activation_blocking_reasons fields added)
  src/apps/provider_portal/services/profile_service.py (_activation_status() helper)
  src/apps/organization_portal/services/viewmodels.py (same 3 fields)
  src/apps/organization_portal/services/profile_service.py (same helper)
  src/templates/provider_portal/profile.html (activation_status.html include)
  src/templates/organization_portal/profile.html (same)
  src/apps/provider_portal/tests/test_profile.py (locked query-count baseline updated
    7 -> 10: 3 new fixed-cost queries from the activation-status lookup, not per-item)
  src/apps/organization_portal/tests/test_profile.py (locked query-count baseline
    updated 7 -> 11, same reason)
Files deleted: None
Database impact: None
Migration impact: None — pure service/permission/view-layer addition; verified via
  makemigrations --check showing identical pre-existing drift only (no new accounts/
  kernel entries; no new model field, no new ProfileStatus value)
Security impact: New platform-scoped permission ACCOUNTS_PROFILE_ACTIVATE, granted only
  to platform_owner/platform_admin/platform_support; self-activation refused as
  defense-in-depth inside the service (mirrors ADM-014's self-review refusal); cross-
  tenant activation refused (profile resolved and tenant-checked before permission
  enforcement, returns not-found); activation refused while ineligible (unverified,
  expired document, suspended profile); concurrent activation attempts serialize via
  select_for_update() and produce exactly one AuditLog record (see ARCHITECTURE_DECISION_LOG
  ADM-016)
Financial impact: None
Tests executed: check (0), makemigrations --check (1, pre-existing unrelated drift only),
  40 new tests across 5 files (all 0) — 11 completion + 16 accounts activation (incl.
  concurrency) + 9 admin_portal view tests + 2 provider_portal + 2 organization_portal
  presentation tests, affected-app Level 2 suite (accounts + provider_portal +
  organization_portal + admin_portal combined) 439/439, full regression 1808/1808 (exit 0)
Result: Success — profile completion is deterministic and single-source-of-truth,
  activation is controlled/audited/authorized/idempotent/concurrency-safe, minimum usable
  platform and owner UI delivered; zero regressions; zero migrations; Phase 1 acceptance
  criteria now fully met (see IMPLEMENTATION_ROADMAP.md)
Rollback method: git revert of the branch's commit(s); no data migration to reverse
Status: Complete — branch phase1-activation-completion-final, PR to be created, NOT merged
```

## Entry 022

```
Change ID: CL-022
Date/time: 2026-07-15 (Phase 1.3 remediation — PR #5 fix activation state semantics)
Task: Make profile.status the sole source of truth for activation state; AuditLog becomes
      historical evidence only, never the activation signal
Reason: PR #5 review found that AuditLog existence, not profile.status, was determining
        "is this profile activated" — because registration left profiles ACTIVE by
        default, ProfileActivationService never performed a real status transition in the
        common case. Root architectural issue corrected before merge.
Files added: None
Files modified:
  src/apps/accounts/services/registration.py (create_caregiver()/create_company_admin()
    now create profiles with status=ProfileStatus.DRAFT, not the ACTIVE model default)
  src/apps/accounts/services/profiles.py (ensure_caregiver_profile() defaults to DRAFT too)
  src/apps/accounts/services/activation_eligibility_service.py (blocking check changed
    from "status != ACTIVE" to "status in (SUSPENDED, ARCHIVED)" — removes the circular
    "must already be ACTIVE to become eligible" rule; reason code renamed
    profile_status_not_active -> profile_status_blocked)
  src/apps/accounts/services/profile_activation_service.py (rewritten: real DRAFT ->
    ACTIVE transition, ProfileActivationResult structured return, idempotency judged by
    profile.status not AuditLog existence, before/after status recorded on AuditLog)
  src/apps/admin_portal/views.py (is_activated(profile) call-site update)
  src/apps/provider_portal/services/profile_service.py (same; activation_profile_status
    passed to the ViewModel)
  src/apps/organization_portal/services/profile_service.py (same)
  src/apps/provider_portal/services/viewmodels.py (activation_profile_status field added)
  src/apps/organization_portal/services/viewmodels.py (same)
  src/templates/provider_portal/profile.html (passes profile_status to the component)
  src/templates/organization_portal/profile.html (same)
  src/ui/components/portal/activation_status.html (explicit SUSPENDED badge branch)
  src/templates/admin_portal/caregiver_activation_detail.html (same)
  src/templates/admin_portal/organization_activation_detail.html (same)
  src/apps/accounts/tests/test_profile_activation.py (rewritten: DRAFT fixtures, new
    ProfileActivationResult assertions, AuditLogIsNotSourceOfTruthTest,
    EligibilitySemanticsTest, organization-suspended coverage)
  src/apps/accounts/tests/test_activation_eligibility.py (renamed reason assertion;
    added archived/draft-eligible/organization-suspended coverage)
  src/apps/accounts/tests/test_registration.py (added DRAFT-on-registration assertions)
  src/apps/admin_portal/tests/test_profile_activation.py (DRAFT fixtures; added
    suspended-activation-refused, suspended-detail-shows-suspended)
  src/apps/provider_portal/tests/test_activation_presentation.py (DRAFT fixture fix)
  src/apps/organization_portal/tests/test_activation_presentation.py (same)
  src/apps/provider_portal/tests/test_profile.py (locked query-count baseline 10 -> 9 —
    is_activated() no longer queries AuditLog)
  src/apps/organization_portal/tests/test_profile.py (locked query-count baseline
    11 -> 10, same reason)
Files deleted: None
Database impact: None
Migration impact: None — CaregiverProfile.status/OrganizationProfile.status's own Django
  field default remains ProfileStatus.ACTIVE, unchanged; only the three canonical
  registration/bootstrap call sites now pass an explicit status=DRAFT override. See
  ARCHITECTURE_DECISION_LOG ADM-016 remediation note for the full "why no model-default
  change" reasoning and the confirmed complete inventory of profile-creation call sites.
Security impact: None new — same ACCOUNTS_PROFILE_ACTIVATE permission, same self-
  activation/cross-tenant refusals, unchanged.
Financial impact: Indirect, out of code scope: a freshly registered caregiver/organization
  is no longer counted ACTIVE by apps.orders.services.eligibility_service
  .OrderEligibilityService.is_eligible()/apps.accounts.services.supplier_bridge
  .is_organization_supplier_active() until platform staff formally activate it. No
  Marketplace/Financial/Booking code was modified — this is the intended consequence of
  activation being a real, explicit action.
Tests executed: check (0), makemigrations --check --dry-run (1, pre-existing unrelated
  drift only, no CaregiverProfile/OrganizationProfile.status field change present), 16 new/
  renamed focused tests (all 0), affected-app Level 2 suite (accounts + admin_portal +
  provider_portal + organization_portal) 455/455 (incl. 2 locked query-count baselines
  updated), full regression 1824/1824 (exit 0)
Result: Success — profile.status is now the sole activation-state source of truth;
  AuditLog is historical evidence only; DRAFT is the real pre-activation registration
  state; zero regressions; zero migrations
Rollback method: git revert of the branch's commit(s); no data migration to reverse
Status: Complete — branch phase1-activation-completion-final, PR #5 updated in place, NOT merged
```

## Entry 023

```
Change ID: CL-023
Date/time: 2026-07-15 (Phase 2.1 — Caregiver Professional Profile Foundation)
Task: Implement the first coherent, production-usable slice of the caregiver
      professional profile — biography reuse, skills, experience, services-offered
      confirmation, verified-credential public summary, and a corrected public/private
      eligibility boundary on the single caregiver public profile page
Reason: Roadmap Phase 2 (Caregiver Profile) opened after Phase 1's close; this slice
        delivers the smallest coherent foundation per explicit task governance, deferring
        gallery/social/financial/order work to later slices
Files added:
  src/apps/accounts/models/professional_profile.py (CaregiverSkill, CaregiverExperience)
  src/apps/accounts/migrations/0006_caregiver_skill_experience.py
  src/apps/accounts/services/caregiver_professional_profile_service.py
    (CaregiverSkillService, CaregiverExperienceService)
  src/apps/accounts/services/public_credential_selector.py (PublicCredentialSelector)
  src/apps/accounts/tests/test_caregiver_professional_profile.py (24 tests)
  src/apps/provider_portal/tests/test_professional_profile.py (13 tests)
  src/apps/public_site/tests/test_professional_profile_public.py (11 tests)
  src/templates/provider_portal/profile_skills.html
  src/templates/provider_portal/profile_experience.html
  src/templates/provider_portal/profile_experience_form.html
Files modified:
  src/apps/accounts/models/__init__.py (export new models)
  src/apps/provider_portal/{views.py,forms.py,urls.py} (skill/experience management views)
  src/apps/provider_portal/services/{profile_service.py,viewmodels.py} (skills/experience
    counts, public_credential_labels)
  src/templates/provider_portal/profile.html (skills/experience sections, credential
    preview panel)
  src/apps/public_site/services/profile_service.py (local, additional public-profile
    eligibility check; skills/experience/credentials assembly)
  src/apps/public_site/services/viewmodels.py (PublicSkillViewModel,
    PublicExperienceViewModel, PublicCredentialViewModel; new fields on
    CaregiverProfileViewModel)
  src/templates/public_site/caregiver_profile.html (skills/experience/credentials
    sections)
  src/apps/provider_portal/tests/test_profile.py (locked query-count baseline 9 -> 12)
  src/apps/public_site/tests/test_profile_service.py (3 fixtures corrected to
    verification_status="verified"; 2 new eligibility tests)
  src/apps/public_site/tests/test_views.py (2 fixtures corrected to
    verification_status="verified")
Files deleted: None
Database impact: Two new tables (accounts_caregiver_skill, accounts_caregiver_experience),
  both FK-child of accounts_caregiver_profile, both empty at migration time (new tables,
  no backfill). No existing table altered.
Migration impact: One new migration (0006_caregiver_skill_experience.py), hand-curated to
  exclude the same pre-existing, unrelated field-alter drift every prior phase's
  makemigrations --check --dry-run has reported (see file header comment for the excluded
  operations). CaregiverProfile.status/OrganizationProfile.status field defaults untouched
  — see ARCHITECTURE_DECISION_LOG ADM-017 Decision 1 for why no model-default change was
  needed for skills/experience/public-profile-metadata.
Security impact: New local eligibility check on the single caregiver public profile page
  (verification_status == VERIFIED, account.is_active) — see ADM-017 Decision 2.
  Owner-only skill/experience editing enforced by _guard_with_caregiver() (account-scoped
  resolution) plus a service-level caregiver=caregiver filter on every mutation. No new
  permission key — ownership, not RBAC, is the boundary, matching
  CaregiverProfileUpdateService's existing shape. Credential summary never exposes file
  path, document number, reviewer identity, or rejection/correction reason (selector
  returns a 3-field dataclass only).
Financial impact: None — orders/booking/commission/finance/payments untouched.
Tests executed: check (0), 50 new focused tests (48 across 3 new files + 2 new eligibility
  tests added to the pre-existing test_profile_service.py) (all 0), affected-app Level 2
  suite (accounts + provider_portal + public_site + orders + organization_portal +
  admin_portal combined) 712/712, makemigrations --check --dry-run (1, pre-existing
  unrelated drift only, confirmed no CaregiverSkill/CaregiverExperience/status-field
  entries present), full regression 1874/1874 (exit 0)
Result: Success — caregiver can manage skills/experience/services-offered (services-
  offered via existing infrastructure); public profile shows skills/experience/verified-
  credential summaries only for genuinely eligible caregivers; private data never
  exposed; zero regressions
Rollback method: git revert of the branch's commit(s); migration 0006 has a clean reverse
  (DROP the two new, empty tables — no data loss, nothing else references them yet)
Status: Complete — branch phase2-caregiver-professional-profile-foundation, PR to be
  created, NOT merged
```
