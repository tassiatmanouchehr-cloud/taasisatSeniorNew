# FILE CHANGE REGISTER

**Repository:** taasisatSenior
**Session:** Offer Marketplace Analysis and Contract Development

---

## FILES ADDED (Documentation/Analysis — Untracked)

| Path | Purpose | Owner Subsystem | Status | Rollback |
|------|---------|----------------|--------|----------|
| `REPORT_1_CURRENT_SYSTEM_FORENSIC_ANALYSIS.md` | Complete codebase forensic analysis | Documentation | Exists, untracked | Delete |
| `REPORT_2_COMPLETION_ASSESSMENT.md` | Evidence-based completion assessment | Documentation | Exists, untracked | Delete |
| `MARKETPLACE_GOLDEN_FLOW_GAP_REPORT.md` | Gap analysis for marketplace golden flow | Documentation | Exists, untracked | Delete |
| `OFFER_MARKETPLACE_CONTRACT.md` | First contract draft (superseded) | Documentation | Exists, untracked | Delete |
| `OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md` | Revised implementation contract | Documentation | Exists, untracked | Delete |

## FILES ADDED (Temporary Validation Scripts — Untracked)

| Path | Purpose | Owner Subsystem | Status | Rollback |
|------|---------|----------------|--------|----------|
| `src/e2e_validation.py` | Standalone E2E workflow validation script | Validation | Exists, untracked | Delete |
| `src/fix_perms.py` | PostgreSQL permission fix script | Environment | Exists, untracked | Delete |
| `src/setup_db.py` | PostgreSQL database setup script | Environment | Exists, untracked | Delete |

## FILES ADDED (Change-Reporting Structure — Untracked)

| Path | Purpose | Owner Subsystem | Status | Rollback |
|------|---------|----------------|--------|----------|
| `mimo change/00_WORK_COMPLETED_TO_DATE.md` | Retrospective record of all work | Documentation | Exists, untracked | Delete directory |
| `mimo change/01_CHANGE_LEDGER.md` | Append-only change ledger | Documentation | Exists, untracked | Delete directory |
| `mimo change/02_ARCHITECTURE_DECISION_LOG.md` | Architecture decisions | Documentation | Exists, untracked | Delete directory |
| `mimo change/03_FILE_CHANGE_REGISTER.md` | This file | Documentation | Exists, untracked | Delete directory |
| `mimo change/04_TEST_EXECUTION_LOG.md` | Test execution history | Documentation | Exists, untracked | Delete directory |
| `mimo change/05_OPEN_QUESTIONS_AND_RISKS.md` | Open questions and risks | Documentation | Exists, untracked | Delete directory |
| `mimo change/06_FINAL_CONTRACT_REMEDIATION_REPORT.md` | Remediation report | Documentation | Exists, untracked | Delete directory |
| `mimo change/07_CONTRACT_DIFF_SUMMARY.md` | Contract diff summary | Documentation | Exists, untracked | Delete directory |
| `mimo change/08_FINAL_TASK_VERIFICATION.md` | Final verification | Documentation | Exists, untracked | Delete directory |
| `PROJECT_CONTINUATION.md` | Permanent project memory for future AI sessions | Documentation | Exists, untracked | Delete |
| `NEXT_TASK.md` | Next task definition | Documentation | Exists, untracked | Delete |

## FILES MODIFIED

| File | Change | Reason |
|------|--------|--------|
| `src/apps/orders/models.py` | Added OrderOfferStatus, OFFER_TERMINAL_STATUSES, OrderOffer with can_edit/can_withdraw/can_select | Phase 1 domain foundation |
| `src/apps/orders/admin.py` | Added OrderOfferAdmin | Phase 1 admin registration |

## FILES DELETED

| File | Reason |
|------|--------|
| `src/apps/orders/migrations/0009_orderoffer_canonical.py` | Squashed into 0008 |
| `src/cleanup_test_db.py` | Temporary tooling removed |
| `src/apps/kernel/migrations/0012_orderoffer.py` | Phantom migration (Django version drift) |
| `src/apps/kernel/migrations/0012_orderoffer_canonical.py` | Phantom migration (Django version drift) |

## FILES PLANNED BUT NOT YET CHANGED (Offer Marketplace Implementation)

The following files would be created or modified if the Offer Marketplace implementation proceeds. These are documented here for traceability but do NOT exist yet.

### New Files (Planned → Implemented Status)

| Path | Purpose | Owner Subsystem | Status |
|------|---------|----------------|--------|
| `src/apps/orders/migrations/0008_orderoffer.py` | OrderOffer model migration (canonical constraint) | Orders | **IMPLEMENTED** |
| `src/apps/orders/tests/test_order_offer_model.py` | Model tests (40 tests) | Orders | **IMPLEMENTED** |
| `src/apps/orders/services/offer_service.py` | OrderOfferService | Orders | Planned (Phase 2) |
| `src/apps/orders/services/discovery_service.py` | OrderDiscoveryService | Orders | Planned (Phase 2) |
| `src/apps/orders/tests/test_offer_service.py` | Service tests | Orders | Planned (Phase 2) |
| `src/apps/orders/tests/test_offer_concurrency.py` | Concurrency tests | Orders | Planned (Phase 2) |
| `src/apps/orders/tests/test_offer_integration.py` | Integration tests | Orders | Planned (Phase 2) |
| `src/apps/portal/templates/portal/offers_compare.html` | Customer comparison page | Portal | Planned (Phase 2) |
| `src/apps/portal/templates/portal/offer_select_confirm.html` | Selection confirmation | Portal | Planned (Phase 2) |
| `src/apps/provider_portal/templates/provider_portal/available_orders.html` | Caregiver order listing | Provider Portal | Planned (Phase 2) |
| `src/apps/provider_portal/templates/provider_portal/offer_form.html` | Offer submit/edit form | Provider Portal | Planned (Phase 2) |
| `src/apps/portal/tests/test_offer_views.py` | Customer portal tests | Portal | Planned (Phase 2) |
| `src/apps/provider_portal/tests/test_offer_views.py` | Caregiver portal tests | Provider Portal | Planned (Phase 2) |

### Modified Files (Planned → Implemented Status)

| Path | Change | Reason | Status |
|------|--------|--------|--------|
| `src/apps/orders/models.py` | Add OrderOfferStatus, OFFER_TERMINAL_STATUSES, OrderOffer (with can_edit/can_withdraw/can_select properties) | New model for offer marketplace | **IMPLEMENTED** |
| `src/apps/orders/admin.py` | Add OrderOfferAdmin | Admin registration | **IMPLEMENTED** |
| `src/apps/payments/models.py` | Add nullable order_offer FK to PaymentIntent | Payment retry linkage (1:N) | Planned (Phase 2) |
| `src/apps/portal/views.py` | Add offers_compare_view, offer_select_view | Customer offer comparison/selection | Planned (Phase 2) |
| `src/apps/portal/urls.py` | Add offer routes | URL patterns for new views | Planned (Phase 2) |
| `src/apps/provider_portal/views.py` | Add available_orders_view, offer_submit/edit/withdraw views | Caregiver offer management | Planned (Phase 2) |
| `src/apps/provider_portal/urls.py` | Add offer routes | URL patterns for new views |
| `src/apps/provider_portal/forms.py` | Add OrderOfferForm | Form for offer submission |
| `src/apps/kernel/events/base.py` | Add ORDER_OFFER_* event type constants | Event type definitions |
| `src/apps/payments/services/payment_callback_service.py` | Wire payment success → confirm_payment | Payment completion wiring |
| `src/apps/orders/services/status_machine.py` | Wire order cancellation → cancel_all_for_order | Cancellation cleanup |
| `src/apps/commission/models/deadline.py` | Add nullable order_offer FK | Deadline reuse for offer hold |
| `src/apps/commission/services/deadline_service.py` | Add offer-hold expiry path in expire_due() | Deadline expiry routing |

---

## 2026-07-14 — Documentation Synchronization (CL-016)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `README.md` | Modified | Point to `project docs/00_START_HERE.md`; remove archived doc links | git checkout |
| `AI_START_HERE.md` | Modified | Short entry point to `project docs/` | git checkout |
| `DOCUMENTATION_RULES.md` | Modified | Point only to `project docs/` | git checkout |
| `PROJECT_CONTINUATION.md` | Modified | Pointer-only (deduplicated) | git checkout |
| `NEXT_TASK.md` | Modified | Pointer-only (deduplicated) | git checkout |
| `project docs/00_START_HERE.md` | Modified | Register IMPLEMENTATION_ROADMAP.md | git checkout |
| `project docs/01_PROJECT_RULES.md` | Modified | Remove canonical docs/mimo change refs | git checkout |
| `project docs/DOCUMENTATION_RULES.md` | Modified | Remove canonical docs/mimo change refs | git checkout |
| `project docs/02_PROJECT_CONTINUATION.md` | Modified | HEAD ce3b30e, Phase 1 committed | git checkout |
| `project docs/03_NEXT_TASK.md` | Modified | BG-001 done; next = roadmap Phase 1 | git checkout |
| `project docs/current/IMPLEMENTATION_STATE.md` | Modified | HEAD + committed Phase 1 | git checkout |
| `project docs/current/SYSTEM_OVERVIEW.md` | Modified | HEAD + maturity + paths | git checkout |
| `project docs/quality/COMPLETION_BACKLOG.md` | Modified | BG-001 complete; BG-002 evidence | git checkout |
| `project docs/quality/LEGACY_AND_DEAD_CODE.md` | Modified | Migration table + drift note | git checkout |
| `project docs/audit/DOCUMENTATION_CONTRADICTIONS.md` | Appended | Resolution update | git checkout |
| `project docs/registry/DOCUMENTATION_REGISTRY.md` | Rewritten | Active list = project docs/ | git checkout |
| `project docs/registry/SUPERSESSION_MAP.md` | Rewritten | Superseded paths updated | git checkout |
| `project docs/IMPLEMENTATION_ROADMAP.md` | Modified | Executed verification evidence | git checkout |
| `project docs/traceability/TEST_EXECUTION_LOG.md` | Appended | Run 008 | append-only |
| `project docs/traceability/CHANGE_LEDGER.md` | Appended | Entry 016 | append-only |

---

## 2026-07-14 — BG-002 Order Number Collision Fix (CL-017)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `src/apps/orders/models.py` | Modified | Bounded savepoint-wrapped retry in `Order.save()`; suffix 4→6 digits; `_is_order_number_collision()` helper | git revert |
| `src/apps/orders/tests/test_order_number_generation.py` | Added | 8 BG-002 regression tests incl. concurrency | Delete |
| `project docs/02_PROJECT_CONTINUATION.md` | Modified | Blocker cleared; phase updated | git checkout |
| `project docs/03_NEXT_TASK.md` | Modified | BG-002 marked done | git checkout |
| `project docs/quality/COMPLETION_BACKLOG.md` | Modified | BG-002 COMPLETE with resolution | git checkout |
| `project docs/quality/DEFECT_AND_RISK_REGISTER.md` | Modified | FR-005 RESOLVED | git checkout |
| `project docs/traceability/CHANGE_LEDGER.md` | Appended | Entry CL-017 | append-only |
| `project docs/traceability/TEST_EXECUTION_LOG.md` | Appended | Run 009 | append-only |
| `project docs/traceability/IMPLEMENTATION_JOURNAL.md` | Appended | BG-002 journal entry | append-only |

---

## 2026-07-14 — Post-Merge Documentation Sync (CL-018)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `project docs/02_PROJECT_CONTINUATION.md` | Modified | HEAD eb51018; Phase 1 ACTIVE | git checkout |
| `project docs/03_NEXT_TASK.md` | Modified | BG-002 merged; Phase 1 ACTIVE | git checkout |
| `project docs/IMPLEMENTATION_ROADMAP.md` | Modified | P0 hygiene/G12 done + merged | git checkout |
| `project docs/quality/COMPLETION_BACKLOG.md` | Modified | BG-002 merge record | git checkout |
| `project docs/current/IMPLEMENTATION_STATE.md` | Modified | HEAD + test counts (1,680) | git checkout |
| `project docs/current/SYSTEM_OVERVIEW.md` | Modified | HEAD eb51018 | git checkout |
| `project docs/traceability/CHANGE_LEDGER.md` | Appended | Entry CL-018 | append-only |
| `project docs/traceability/IMPLEMENTATION_JOURNAL.md` | Appended | PR #1 merge record | append-only |

---

## 2026-07-15 — Phase 1.1 Manual Document Verification (CL-019)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `src/apps/accounts/migrations/0005_add_correction_required_document_status.py` | Added | CORRECTION_REQUIRED choice, hand-trimmed to exclude unrelated drift | Reverse migration |
| `src/apps/accounts/services/verification_review_service.py` | Added | Approve/reject/request_correction with locking, tenant scope, audit | Delete |
| `src/apps/accounts/services/verification_evaluator.py` | Added | AI evaluator Protocol placeholder, no implementation | Delete |
| `src/apps/accounts/tests/test_verification_review.py` | Added | 25 service-layer tests incl. concurrency | Delete |
| `src/apps/admin_portal/tests/test_document_verification.py` | Added | 16 view-layer/security tests | Delete |
| `src/templates/admin_portal/document_verification_queue.html` | Added | Review queue page | Delete |
| `src/templates/admin_portal/document_verification_detail.html` | Added | Detail + review form page | Delete |
| `src/apps/accounts/models/media.py` | Modified | CORRECTION_REQUIRED status; docstrings updated (ADM-014) | git checkout |
| `src/apps/kernel/permissions/keys.py` | Modified | ACCOUNTS_DOCUMENT_REVIEW registered | git checkout |
| `src/apps/accounts/permission_keys.py` | Modified | Re-export | git checkout |
| `src/apps/admin_portal/permission_keys.py` | Modified | Re-export as DOCUMENT_REVIEW | git checkout |
| `src/apps/kernel/role_catalog.py` | Modified | Granted to platform_owner/admin/support | git checkout |
| `src/apps/admin_portal/forms.py` | Modified | DocumentReviewForm | git checkout |
| `src/apps/admin_portal/views.py` | Modified | 4 new views | git checkout |
| `src/apps/admin_portal/urls.py` | Modified | 4 new routes | git checkout |
| `src/templates/admin_portal/home.html` | Modified | Nav card | git checkout |
| `src/ui/components/portal/verification_badge.html` | Modified | correction_required branch | git checkout |
| `src/ui/components/portal/document_status.html` | Modified | Docstring only (action_message semantics) | git checkout |
| `src/templates/provider_portal/document_upload.html` | Modified | action_message wired to real reason | git checkout |
| `src/templates/organization_portal/document_upload.html` | Modified | Same | git checkout |
| `project docs/*` (multiple) | Modified | Doc sync — see IMPLEMENTATION_JOURNAL for full narrative | git checkout |

---

## 2026-07-15 — Phase 1.2 Verification Completion and Activation Rules (CL-020)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `src/apps/accounts/services/document_ownership.py` | Added | Shared tenant/owner resolution for VerificationDocument | Delete |
| `src/apps/accounts/services/verification_policy.py` | Added | RequiredDocumentPolicy (Part A) | Delete |
| `src/apps/accounts/services/verification_rollup_service.py` | Added | ProfileVerificationRollupService (Part B) | Delete |
| `src/apps/accounts/services/activation_eligibility_service.py` | Added | ActivationEligibilityService (Part D) | Delete |
| `src/apps/accounts/tests/test_verification_policy.py` | Added | 13 policy tests | Delete |
| `src/apps/accounts/tests/test_verification_rollup.py` | Added | 13 roll-up tests incl. concurrency | Delete |
| `src/apps/accounts/tests/test_document_resubmission.py` | Added | 10 resubmission tests incl. concurrency | Delete |
| `src/apps/accounts/tests/test_activation_eligibility.py` | Added | 11 eligibility tests | Delete |
| `src/apps/accounts/services/document_service.py` | Modified | resubmit() added (Part C) | git checkout |
| `src/apps/accounts/services/profiles.py` | Modified | calculate_organization_profile_completion() added | git checkout |
| `src/apps/accounts/services/verification_review_service.py` | Modified | Delegates ownership helpers; syncs roll-up | git checkout |
| `src/apps/provider_portal/views.py` | Modified | Uses DocumentService.resubmit() | git checkout |
| `src/apps/organization_portal/views.py` | Modified | Same | git checkout |
| `project docs/*` (multiple) | Modified | Doc sync — see IMPLEMENTATION_JOURNAL | git checkout |

---

## 2026-07-15 — Phase 1.3 Complete Phase 1 Activation and Profile Completion (CL-021)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `src/apps/accounts/services/profile_completion_service.py` | Added | ProfileCompletionService (Part A) — single source of truth for base-field checklist | Delete |
| `src/apps/accounts/services/profile_activation_service.py` | Added | ProfileActivationService (Part B/C) | Delete |
| `src/apps/accounts/tests/test_profile_completion.py` | Added | 11 completion tests | Delete |
| `src/apps/accounts/tests/test_profile_activation.py` | Added | 16 activation service tests incl. concurrency | Delete |
| `src/apps/admin_portal/tests/test_profile_activation.py` | Added | 9 view/security tests | Delete |
| `src/apps/provider_portal/tests/test_activation_presentation.py` | Added | 2 owner-facing UI tests | Delete |
| `src/apps/organization_portal/tests/test_activation_presentation.py` | Added | 2 owner-facing UI tests | Delete |
| `src/templates/admin_portal/caregiver_activation_detail.html` | Added | Platform activation detail + action page | Delete |
| `src/templates/admin_portal/organization_activation_detail.html` | Added | Same, organization | Delete |
| `src/ui/components/portal/activation_status.html` | Added | Reusable owner-facing activation status component | Delete |
| `src/apps/accounts/services/profiles.py` | Modified | Completion percentage delegates to ProfileCompletionService | git checkout |
| `src/apps/kernel/permissions/keys.py` | Modified | ACCOUNTS_PROFILE_ACTIVATE registered | git checkout |
| `src/apps/accounts/permission_keys.py` | Modified | Re-export | git checkout |
| `src/apps/admin_portal/permission_keys.py` | Modified | Re-export as PROFILE_ACTIVATE | git checkout |
| `src/apps/kernel/role_catalog.py` | Modified | DOCUMENT_REVIEW_PERMISSIONS renamed PLATFORM_VERIFICATION_PERMISSIONS, includes ACCOUNTS_PROFILE_ACTIVATE | git checkout |
| `src/apps/admin_portal/views.py` | Modified | 4 new activation views | git checkout |
| `src/apps/admin_portal/urls.py` | Modified | 4 new routes | git checkout |
| `src/templates/admin_portal/document_verification_queue.html` | Modified | Owner name links to activation detail | git checkout |
| `src/templates/admin_portal/document_verification_detail.html` | Modified | Same, owner row | git checkout |
| `src/apps/provider_portal/services/viewmodels.py` | Modified | is_activated/activation_eligible/activation_blocking_reasons | git checkout |
| `src/apps/provider_portal/services/profile_service.py` | Modified | _activation_status() helper | git checkout |
| `src/apps/organization_portal/services/viewmodels.py` | Modified | Same 3 fields | git checkout |
| `src/apps/organization_portal/services/profile_service.py` | Modified | Same helper | git checkout |
| `src/templates/provider_portal/profile.html` | Modified | activation_status.html include | git checkout |
| `src/templates/organization_portal/profile.html` | Modified | Same | git checkout |
| `src/apps/provider_portal/tests/test_profile.py` | Modified | Locked query-count baseline 7 -> 10 (fixed-cost activation lookup) | git checkout |
| `src/apps/organization_portal/tests/test_profile.py` | Modified | Locked query-count baseline 7 -> 11, same reason | git checkout |
| `project docs/*` (multiple) | Modified | Doc sync — see IMPLEMENTATION_JOURNAL | git checkout |

---

## 2026-07-15 — Phase 1.3 Remediation: Fix Activation State Semantics (PR #5, CL-022)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `src/apps/accounts/services/registration.py` | Modified | create_caregiver()/create_company_admin() create profiles as DRAFT, not ACTIVE | git checkout |
| `src/apps/accounts/services/profiles.py` | Modified | ensure_caregiver_profile() defaults to DRAFT | git checkout |
| `src/apps/accounts/services/activation_eligibility_service.py` | Modified | Blocks SUSPENDED/ARCHIVED only, not "status != ACTIVE" (removes circularity) | git checkout |
| `src/apps/accounts/services/profile_activation_service.py` | Rewritten | Real DRAFT->ACTIVE transition; status-based idempotency; ProfileActivationResult | git checkout |
| `src/apps/admin_portal/views.py` | Modified | is_activated(profile) call-site update | git checkout |
| `src/apps/provider_portal/services/profile_service.py` | Modified | Same; passes activation_profile_status | git checkout |
| `src/apps/organization_portal/services/profile_service.py` | Modified | Same | git checkout |
| `src/apps/provider_portal/services/viewmodels.py` | Modified | activation_profile_status field added | git checkout |
| `src/apps/organization_portal/services/viewmodels.py` | Modified | Same | git checkout |
| `src/templates/provider_portal/profile.html` | Modified | Passes profile_status to activation_status.html | git checkout |
| `src/templates/organization_portal/profile.html` | Modified | Same | git checkout |
| `src/ui/components/portal/activation_status.html` | Modified | Explicit SUSPENDED badge branch | git checkout |
| `src/templates/admin_portal/caregiver_activation_detail.html` | Modified | Same | git checkout |
| `src/templates/admin_portal/organization_activation_detail.html` | Modified | Same | git checkout |
| `src/apps/accounts/tests/test_profile_activation.py` | Rewritten | DRAFT fixtures; ProfileActivationResult assertions; AuditLog-not-source-of-truth test | git checkout |
| `src/apps/accounts/tests/test_activation_eligibility.py` | Modified | Reason-code rename; archived/draft-eligible/org-suspended coverage | git checkout |
| `src/apps/accounts/tests/test_registration.py` | Modified | DRAFT-on-registration assertions | git checkout |
| `src/apps/admin_portal/tests/test_profile_activation.py` | Modified | DRAFT fixtures; suspended-activation coverage | git checkout |
| `src/apps/provider_portal/tests/test_activation_presentation.py` | Modified | DRAFT fixture fix | git checkout |
| `src/apps/organization_portal/tests/test_activation_presentation.py` | Modified | Same | git checkout |
| `src/apps/provider_portal/tests/test_profile.py` | Modified | Locked query-count baseline 10 -> 9 (AuditLog query removed) | git checkout |
| `src/apps/organization_portal/tests/test_profile.py` | Modified | Locked query-count baseline 11 -> 10, same reason | git checkout |
| `project docs/*` (multiple) | Modified | Doc sync — see IMPLEMENTATION_JOURNAL | git checkout |

---

## 2026-07-15 — Phase 2.1 Caregiver Professional Profile Foundation (CL-023)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `src/apps/accounts/models/professional_profile.py` | Added | CaregiverSkill, CaregiverExperience models | Delete |
| `src/apps/accounts/migrations/0006_caregiver_skill_experience.py` | Added | New tables for the two models above | Reverse migration (DROP, empty tables) |
| `src/apps/accounts/services/caregiver_professional_profile_service.py` | Added | CaregiverSkillService, CaregiverExperienceService | Delete |
| `src/apps/accounts/services/public_credential_selector.py` | Added | PublicCredentialSelector | Delete |
| `src/apps/accounts/tests/test_caregiver_professional_profile.py` | Added | 24 service-layer tests | Delete |
| `src/apps/provider_portal/tests/test_professional_profile.py` | Added | 13 view-layer tests | Delete |
| `src/apps/public_site/tests/test_professional_profile_public.py` | Added | 11 public-profile tests | Delete |
| `src/templates/provider_portal/profile_skills.html` | Added | Skill management page | Delete |
| `src/templates/provider_portal/profile_experience.html` | Added | Experience list page | Delete |
| `src/templates/provider_portal/profile_experience_form.html` | Added | Experience add/edit form | Delete |
| `src/apps/accounts/models/__init__.py` | Modified | Export new models | git checkout |
| `src/apps/provider_portal/views.py` | Modified | Skill/experience management views | git checkout |
| `src/apps/provider_portal/forms.py` | Modified | SkillForm, ExperienceForm | git checkout |
| `src/apps/provider_portal/urls.py` | Modified | New skill/experience routes | git checkout |
| `src/apps/provider_portal/services/profile_service.py` | Modified | skills_count/experience_count/public_credential_labels | git checkout |
| `src/apps/provider_portal/services/viewmodels.py` | Modified | New fields + SkillRowViewModel/ExperienceRowViewModel | git checkout |
| `src/templates/provider_portal/profile.html` | Modified | Skills/experience sections, credential preview panel | git checkout |
| `src/apps/public_site/services/profile_service.py` | Modified | Local eligibility check; skills/experience/credentials assembly | git checkout |
| `src/apps/public_site/services/viewmodels.py` | Modified | New public ViewModels and fields | git checkout |
| `src/templates/public_site/caregiver_profile.html` | Modified | Skills/experience/credentials sections | git checkout |
| `src/apps/provider_portal/tests/test_profile.py` | Modified | Locked query-count baseline 9 -> 12 | git checkout |
| `src/apps/public_site/tests/test_profile_service.py` | Modified | 3 fixtures corrected to verification_status="verified"; 2 new tests | git checkout |
| `src/apps/public_site/tests/test_views.py` | Modified | 2 fixtures corrected to verification_status="verified" | git checkout |
| `project docs/*` (multiple) | Modified | Doc sync — see IMPLEMENTATION_JOURNAL | git checkout |

---

## 2026-07-15 — Phase 2.1 Remediation: Close Public Caregiver Visibility Gap BG-022 (CL-024)

| Path | Change | Purpose | Rollback |
|------|--------|---------|----------|
| `src/apps/public_site/tests/test_public_visibility_policy.py` | Added | 13 tests proving one canonical rule across all public surfaces | Delete |
| `src/apps/public_site/services/common.py` | Modified | is_publicly_visible_attrs() now the single canonical rule (+ verification + account-active) | git checkout |
| `src/apps/public_site/services/profile_service.py` | Modified | Removed now-redundant local duplicate eligibility check | git checkout |
| `src/apps/accounts/services/supplier_bridge.py` | Modified | select_related("user")/("admin_user") added to resolve_supplier_entities_bulk() | git checkout |
| `src/apps/public_site/tests/helpers.py` | Modified | verification_status fixture default corrected "unverified" -> "verified" | git checkout |
| `src/apps/public_site/tests/test_professional_profile_public.py` | Modified | Query-count assertion 14 -> 13 | git checkout |
| `project docs/*` (multiple) | Modified | Doc sync — see IMPLEMENTATION_JOURNAL | git checkout |
