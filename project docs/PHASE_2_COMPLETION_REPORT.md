# PHASE 2 COMPLETION REPORT — Caregiver Professional Profile

**Phase:** Roadmap Phase 2 (`IMPLEMENTATION_ROADMAP.md`)
**Sprints:** Phase 2.1 (Foundation) + BG-022 remediation, Sprint 2.2 (Gallery), Sprint 2.3
(Credibility Layer), Sprint 2.4 (Availability), Sprint 2.5 (Dashboard), Sprint 2.6 (Public
Profile Finalization and Phase 2 Acceptance)
**Report date:** 2026-07-15
**Final branch:** `phase2-caregiver-public-profile-finalization` (from merged `main` @
`9a260241cfd82ef3be997eec152d1aa2a510542b`, PR #10)

---

## 1. Executive Summary

Phase 2 delivers the caregiver professional profile as one coherent, secure, discoverable,
accessible, performant, documented capability: a caregiver can build a public profile
(biography, headline, skills, experience, verified-credential summaries, precise
verification badges, media gallery, weekly availability), manage every part of it with
clear owner-only mutation boundaries and per-item visibility control, and see a complete
dashboard of their own work, earnings, invoices, and reputation. Customers can discover and
view that profile through the directory, search, home page, and the profile's own detail
page — all resolving through one canonical public-visibility policy, so a caregiver's
discoverability in a listing and their detail page's own accessibility can never diverge.

Sprint 2.6 closes Phase 2 as an integration/quality/privacy/accessibility/performance
sprint: it did not add new capability, it proved the existing capability composes correctly,
fixed the accessibility/SEO/redundant-claim defects found while proving it, measured query
behavior across every caregiver-related page, and confirmed the existing cache and API
surfaces need no change for Phase 2 to be considered complete.

**Phase 2 acceptance criteria are satisfied**, with one explicitly accepted external-domain
dependency: no canonical bonus/penalty representation exists anywhere in this repository
(KL-020) — documented as a financial-domain gap, not a caregiver-profile defect, per this
sprint's own governance (Section L).

---

## 2. Phase 2 Scope Delivered

| Capability | Delivered in |
|---|---|
| Professional biography/headline/specialty/years-experience/service-radius | Phase 2.1 (owner edit reused pre-existing Epic 06 UI) |
| Skills management (add/remove/visibility toggle) | Phase 2.1 + Sprint 2.3 (visibility) |
| Experience management (add/edit/delete/visibility) | Phase 2.1 + Sprint 2.3 (visibility) |
| Verified-credential public summaries | Phase 2.1 (`PublicCredentialSelector`) |
| Precise verification badges (profile/identity/credential, distinct from a single generic pill) | Sprint 2.3 |
| Derived professional highlights (years, verified-credential count, visible-skill count, completed jobs, reviews) | Sprint 2.3 |
| Media gallery (upload/caption/alt-text/reorder/visibility/remove) | Sprint 2.2 |
| Weekly availability (working windows, overlap/duplicate refusal, blocked periods, canonical evaluator, public day-label summary) | Sprint 2.4 |
| Availability mutation concurrency safety | Sprint 2.4 + PR #9 remediation |
| Caregiver professional dashboard (work summary, financial overview, wallet movements, invoice summary, reviews/reputation, statistics) | Sprint 2.5 |
| Canonical public-visibility policy (directory/home/detail page unified) | Phase 2.1 + BG-022 remediation |
| Public profile page composition, SEO metadata correctness, accessibility, redundant-badge removal, query-count measurement, Phase 2 E2E acceptance | Sprint 2.6 |

Explicitly not delivered (out of Phase 2's own scope, recorded as future roadmap work):
Company Portal features, Customer Portal features, new marketplace order-state transitions,
new invoice/payment/settlement behavior, a bonus/penalty financial model, social
feed/follows/likes/comments, external calendar integration, AI moderation.

---

## 3. Models Added

| Model | Sprint | Migration |
|---|---|---|
| `CaregiverSkill` | Phase 2.1 | `accounts/0006_caregiver_skill_experience.py` |
| `CaregiverExperience` | Phase 2.1 | `accounts/0006_caregiver_skill_experience.py` |
| `CaregiverGalleryItem` | Sprint 2.2 | `accounts/0007_caregiver_gallery_item.py` |

No models added in Sprint 2.3, 2.4, 2.5, or 2.6 — each reused pre-existing models
(`VerificationDocument`, `ProviderWorkingWindow`, `AvailabilityBlockedPeriod`,
`CapacityRule`, `Order`, `FinancialDocument`, `WalletTransaction`, `Review`) or added no
schema-touching code at all (Sprint 2.6: templates, tests, documentation only).

---

## 4. Services/Selectors Added

- `CaregiverSkillService`, `CaregiverExperienceService` (Phase 2.1; `toggle_visibility()` on
  the former, `is_visible` parameter on the latter's `create()`/`update()` — Sprint 2.3)
- `PublicCredentialSelector` (Phase 2.1) — safe, 3-field public credential projection
- `CaregiverGalleryService`, `apps.accounts.services.image_validation.validate_image()`
  (Sprint 2.2; transaction-safe file lifecycle + decompression-bomb hardening — PR #7
  remediation)
- `RequiredDocumentPolicy.is_expiring_soon()` (Sprint 2.3)
- `AvailabilityQueryService.evaluate()`/`get_distinct_active_days()`,
  `AvailabilityMutationService` overlap/duplicate refusal + `toggle_working_window()`
  (Sprint 2.4; supplier-row locking — PR #9 concurrency remediation)
- `CaregiverDashboardPresentationService`; `OrderQueryService.list_for_supplier()`/
  `count_by_status_for_supplier()`; `FinancialDocumentService.list_for_beneficiary_party()`/
  `count_by_status_for_beneficiary_party()`; `ReputationService
  .list_recent_reviews_with_reviewer_names()` (Sprint 2.5)
- `common.is_publicly_visible_attrs()` (BG-022 remediation, Phase 2.1) — the single
  canonical public-visibility function every public surface routes through

No new services/selectors added in Sprint 2.6 — it fixed template-level defects
(`caregiver_profile.html` and 4 `provider_portal` templates) in existing presentation logic
and added one new cross-app test file.

---

## 5. Routes/Views/Templates Added

No new URL routes in any Phase 2 sprint, including Sprint 2.6. New/extended templates:

- `templates/provider_portal/profile_skills.html`, `profile_experience_form.html` (Phase
  2.1); `profile_gallery.html`, `profile_gallery_item_edit.html` (Sprint 2.2);
  `availability.html` (Sprint 2.4, extended with edit/toggle UI); `dashboard.html` (Sprint
  2.5, five new sections)
- `templates/public_site/caregiver_profile.html` — extended every sprint (skills/
  experience/credentials Phase 2.1; gallery Sprint 2.2; badges/highlights Sprint 2.3;
  schedule summary Sprint 2.4; SEO/accessibility/redundant-badge fixes Sprint 2.6)

Sprint 2.6 template changes (no new views): `caregiver_profile.html` (SEO `page_url`/
`canonical_url`, gallery alt-text fallback, removed redundant badge),
`provider_portal/profile_gallery.html`, `profile_gallery_item_edit.html`,
`availability.html`, `profile_skills.html` (alt-text/label-association fixes).

---

## 6. Permissions Added or Reused

**No new permission key was added anywhere in Phase 2.** Every caregiver-owned mutation
(skills, experience, gallery, availability) is authorized by ownership — the caller's own
`request.user.caregiver_profile`, resolved server-side, never accepted from the request —
mirroring `CaregiverProfileUpdateService`'s existing pattern, not RBAC. `ACCOUNTS_PROFILE_
ACTIVATE` and `ACCOUNTS_DOCUMENT_REVIEW` (both Phase 1) are reused unchanged for activation
and credential review. `DISCOVERY_SUPPLIERS_READ` (pre-existing, unrelated internal API) was
reviewed in Sprint 2.6 Section I and confirmed out of scope for the public profile.

---

## 7. Migrations

| Sprint | Migration | Change |
|---|---|---|
| Phase 2.1 | `accounts/0006_caregiver_skill_experience.py` | 2 new tables (`CaregiverSkill`, `CaregiverExperience`) |
| Sprint 2.2 | `accounts/0007_caregiver_gallery_item.py` | 1 new table (`CaregiverGalleryItem`) |
| Sprint 2.3, 2.4, 2.5, 2.6 | None | Zero schema change |

`python manage.py makemigrations --check` confirmed, at every sprint boundary including
Sprint 2.6's final check, only pre-existing, unrelated cosmetic drift (`kernel
.ServiceSupplier`/`UserAccount` field alters) — never new drift introduced by Phase 2 work.

---

## 8. Public/Private Data Boundary

Every public-facing ViewModel (`apps.public_site.services.viewmodels`,
`apps.accounts.services.public_credential_selector.PublicCredentialSummary`) is a frozen
dataclass with an explicit, fixed field set — never a raw model instance passed to a
template. Structurally, none of these carry a phone number, private email, private address,
national identifier, document file/path, document number, internal document-reviewer
identity, rejection/correction reason, audit-log data, private (non-`is_visible`) gallery
item, private experience/skill entry, vacation/time-off reason, order-customer detail, or
wallet/financial value. `PublicCredentialSelector.for_caregiver()` only ever returns
APPROVED, unexpired, caregiver-owned documents' `document_type`/`label`/`expiry_date` — no
`file`, no `reviewed_by`, no `reviewer_note`, no rejection reason (Phase 2.1, re-confirmed
Sprint 2.6). A customer review's `reviewer_name` (a customer's own name on their own
submitted review) is an intentional, public, non-private field — distinct from, and never
to be confused with, `VerificationDocument.reviewed_by` (the internal document-moderation
reviewer, never exposed).

Owner mutation boundaries: `CaregiverSkillService`, `CaregiverExperienceService`,
`CaregiverGalleryService`, and `AvailabilityMutationService` all re-verify
`record.caregiver_id == caregiver.id` (or the equivalent supplier check) before touching
any specific row — never trusting a caller-supplied ownership claim.

Hidden/DRAFT/SUSPENDED/ARCHIVED/unverified/inactive-account profiles are not publicly
discoverable on any surface: `common.is_publicly_visible_attrs()` (BG-022) is the single
function every public entry point (directory, home, detail page) calls, directly or via
`bulk_supplier_attrs()`.

---

## 9. Security and Tenancy Review

No new attack surface introduced by Phase 2. Every new selector added across Sprints 2.1-2.5
filters by the caller's own supplier/party/tenant_id, resolved once at the top of the
relevant view, never accepted as a request parameter — proven by explicit
cross-caregiver/cross-tenant/customer/unrelated-organization-user denial tests in each
sprint's own test suite (most recently `apps.provider_portal.tests
.test_professional_dashboard`'s four isolation tests, Sprint 2.5). Sprint 2.6 added a
further cross-app proof (`apps.public_site.tests.test_phase2_acceptance
.Phase2DashboardIsolationAcceptanceTest`) confirming one caregiver's dashboard never
contains another's data, and a direct response-body assertion
(`Phase2FullLifecycleAcceptanceTest`) that a populated public profile page never contains
the caregiver's own phone number, a pending credential's file name, an approved credential's
internal UUID, or the internal document reviewer's name.

Concurrency: `CaregiverGalleryService.add_item()` (Sprint 2.2) and
`AvailabilityMutationService.add_working_window()`/`update_working_window()` (Sprint 2.4,
hardened by the PR #9 remediation) both row-lock the owning parent before their
check-then-write, proven against real concurrent transactions by `TransactionTestCase` +
`threading.Barrier` tests, never merely asserted.

Tenancy: every Phase 2 selector accepts and filters by `tenant_id` explicitly; no Phase 2
addition relies on implicit/global querysets.

---

## 10. Accessibility Review

Sprint 2.6 fixed the following, scoped to caregiver-profile-related templates only:

- Non-empty `alt` text on gallery images that previously could render `alt=""` on
  non-decorative content (`CaregiverGalleryItem.alt_text`/`.caption` are both
  `blank=True`) — a Persian fallback ("تصویر گالری") added in `caregiver_profile.html`,
  `profile_gallery.html`, `profile_gallery_item_edit.html`.
- `<label for="{{ field.id_for_label }}">` association, missing on 4 `provider_portal`
  templates (`availability.html` x2, `profile_gallery.html`, `profile_gallery_item_edit
  .html`, `profile_skills.html`); 3 other candidate templates (`profile_edit_basic.html`,
  `profile_edit_professional.html`, `profile_experience_form.html`) were inspected and
  already had this correctly.

Already correct, re-confirmed (not changed): heading hierarchy on the public profile page
(`h1` display name → `h2` section headings, single level, no skips); `role="search"`/
`aria-label` on directory/home search forms; `aria-current="page"`/`aria-label` on
pagination controls; badge components (`ui/components/feedback/badge.html`) that already
carry text labels, not color-only semantics; RTL-compatible markup throughout (no new
LTR-only elements introduced); empty states use the existing semantic `empty_state.html`
component.

Deferred, out of scope: the identical unassociated-label pattern in 12 other templates
across `organization_portal`, `admin_portal`, and `portal` (customer) — not
caregiver-profile templates.

---

## 11. Query/Performance Review

All 7 pages required by this sprint's governance measured directly (via `assertNumQueries`/
`CaptureQueriesContext` in the test suite):

| Page | Query count | Status |
|---|---|---|
| Empty public profile | 15 | Bounded (pre-existing test) |
| Populated public profile | 15 | Bounded — proven not to grow with skill/experience/credential/gallery count |
| Directory (many caregivers) | 28 / 43 / 57 at 5 / 10 / 20 matching candidates | Grows with total matching candidates before pagination — `DiscoveryRankingService.rank()` (KL-012), a shared `apps.discovery` domain-engine limitation, not fixed this sprint |
| Search with filters | Same service as directory; correct results, output page bounded to `PAGE_SIZE=12` | New test proves correctness at scale |
| Home featured providers | 27 / 32 / 42 at the same candidate counts | Same KL-012 cause; output capped at 4 cards regardless of candidate count |
| Provider dashboard | 30 (populated) / 31 (empty) | Bounded (Sprint 2.5), proven not to grow with wallet-transaction count |
| Provider profile-management page | 15 | Bounded (pre-existing), proven not to grow with document/order count |

The dashboard's ~30-query count was reviewed for safe consolidation opportunity per this
sprint's own governance note; no consolidation was applied, because the queries are already
bounded/non-growing and any further reduction would require coupling the financial, order,
invoice, wallet, and reviews domains into a single cross-domain query — an inappropriate
coupling this sprint's governance explicitly warns against. Directory/home's KL-012 growth
was measured and quantified this sprint (previously only qualitatively documented) but not
fixed, since fixing it requires changing `apps.discovery`'s shared ranking engine — out of
scope for a profile-integration sprint that explicitly forbids redesigning domain engines.

Caching: no new cache introduced. A real, production-configured cache exists (Redis with
LocMemCache fallback), but its only existing usage is narrow config/feature-flag caching
with explicit invalidation — never a page/read-model cache — and no proven performance
blocker was found that would justify introducing one. See `ARCHITECTURE_DECISION_LOG.md`
ADM-022 Decision 2.

---

## 12. Test Summary

| Sprint | New tests | Full regression at that point |
|---|---|---|
| Phase 2.1 (+ BG-022 remediation) | 63 | 1887/1887 |
| Sprint 2.2 (+ PR #7 remediation) | 61 | 1948/1948 |
| Sprint 2.3 | 36 | 1984/1984 |
| Sprint 2.4 (+ PR #9 concurrency remediation) | 49 | 2033/2033 |
| Sprint 2.5 | 44 | 2077/2077 |
| Sprint 2.6 | 5 (+ 1 pre-existing test fixed) | 2082/2082 |
| **Phase 2 total new tests** | **258** | — |

Sprint 2.6 test levels: `manage.py check` (0), focused new file
(`apps.public_site.tests.test_phase2_acceptance`, 5/5), directly affected apps
(`apps.public_site` + `apps.provider_portal`, 270/270), `apps.accounts` (368/368, the app
containing the fixed pre-existing test), full regression run twice — once surfacing a
genuinely pre-existing, environment-clock-dependent flaky failure unrelated to this sprint's
own changes (`test_expired_document_does_not_appear`, diagnosed and fixed in one line), once
green (2082/2082).

---

## 13. Documentation/Traceability Summary

All 16 required active documentation files updated this sprint: `02_PROJECT_CONTINUATION
.md`, `03_NEXT_TASK.md`, `IMPLEMENTATION_ROADMAP.md`, `current/IMPLEMENTATION_STATE.md`,
`current/DATA_RELATIONSHIPS.md`, `current/RUNTIME_WORKFLOWS.md`, `current/PERMISSIONS_AND_
TENANCY.md`, `current/PORTALS_AND_APIS.md`, `current/FINANCIAL_SYSTEM.md`, `quality
/COMPLETION_BACKLOG.md` (+BG-027), `quality/DEFECT_AND_RISK_REGISTER.md` (+KL-021),
`quality/TEST_CONFIDENCE_MATRIX.md`, `traceability/CHANGE_LEDGER.md` (+CL-031),
`traceability/FILE_CHANGE_REGISTER.md`, `traceability/TEST_EXECUTION_LOG.md` (+Run 021b,
Run 022), `traceability/IMPLEMENTATION_JOURNAL.md`. `ARCHITECTURE_DECISION_LOG.md` gained
one genuine new entry, ADM-022, recording the sprint's five scope-boundary judgment calls
(redundant-badge removal, no caching, no new API, KL-012 measured-not-fixed, the
pre-existing test fix). PR #10's merge metadata (merge commit
`9a260241cfd82ef3be997eec152d1aa2a510542b`) was recorded during this sprint, as instructed,
rather than in a separate documentation-only PR.

---

## 14. Deferred Items

All explicitly recorded, none silently dropped:

1. **Bonus/penalty financial model (KL-020)** — no canonical representation exists anywhere
   in this repository; documented via `FinancialOverviewViewModel.bonus_penalty_note`
   rather than invented. This is the one Phase 2 acceptance criterion satisfied only as an
   accepted external-domain dependency (see Section 16).
2. **Organization-profile SEO `page_url` bug (KL-021 / BG-027)** — identical to the
   caregiver-profile bug fixed this sprint; deliberately left unfixed, out of caregiver-only
   scope.
3. **Directory/home ranking-engine N+1 (KL-012)** — measured and quantified this sprint, not
   fixed; a shared `apps.discovery` domain-engine change, explicitly out of scope.
4. **Unassociated-`<label>` pattern in `organization_portal`/`admin_portal`/`portal`
   templates** — out of caregiver-profile-only scope.
5. **Skill catalog/normalization (KL-016)** — `CaregiverSkill.name` remains free-text; a
   future modeling decision, not a UI-completion task.
6. **Per-caregiver time zone (KL-018 / BG-024)** — platform-default time zone used
   throughout; no evidence of multi-time-zone demand.
7. **Gallery orphan-file cleanup/retry (KL-014)** and **fixed, non-tenant-configurable image
   dimension limits (KL-015)** — both deliberate simplicity choices from Sprint 2.2.
8. **Production media storage strategy** (local `FileField`, no S3/CDN) — a pre-existing,
   unresolved roadmap-level dependency, unchanged by any Phase 2 sprint.
9. **Extended financial reporting/exports and full orders-history pages** (remaining BG-021
   scope) — Company/Reporting-Portal-scale features, explicitly outside Phase 2's own
   caregiver-public-profile mandate.
10. **New public API for caregiver profiles** — reviewed (Section I), not required by any
    current flow; existing public HTML surfaces already serve the need.
11. **Caching layer** — reviewed (Section H), no proven performance blocker; existing cache
    infra's established pattern does not fit per-request read models without a broader
    invalidation design.

---

## 15. Remaining Risks

- **KL-012 (directory/home ranking N+1)** is the most significant remaining performance
  risk: query count grows linearly with total matching candidates before pagination, not
  just page size. At the scales measured (5/10/20 candidates), this stays well within a
  single request's practical budget, but it has not been measured at production-realistic
  candidate counts (hundreds+) and would eventually require a `apps.discovery` ranking-engine
  change to bound.
- **Bonus/penalty (KL-020)** remains a genuine financial-domain modeling gap; any future
  attempt to surface caregiver bonuses/penalties on the dashboard requires a prior
  Financial Engine Review, not an extension of the current wallet/transaction model.
- **Media storage** (local filesystem) is a known production-readiness gap affecting every
  caregiver-uploaded image (avatar, cover, gallery) equally — unchanged, not worsened, by
  Phase 2.
- **Accessibility** fixes this sprint were scoped to caregiver-profile templates only; the
  same defect patterns exist elsewhere in the repository and will resurface in any future
  accessibility audit of those other portals.

No new critical or high-severity risk was introduced by Phase 2 as a whole.

---

## 16. Complete Phase 2 Acceptance Checklist

| # | Criterion | Status |
|---|---|---|
| 1 | Professional biography/headline works | ✅ Satisfied (Phase 2.1) |
| 2 | Skills management works | ✅ Satisfied (Phase 2.1 + Sprint 2.3 visibility) |
| 3 | Experience management works | ✅ Satisfied (Phase 2.1 + Sprint 2.3 visibility) |
| 4 | Verified credential summaries work | ✅ Satisfied (Phase 2.1) |
| 5 | Precise verification badges work | ✅ Satisfied (Sprint 2.3) |
| 6 | Gallery/media management works | ✅ Satisfied (Sprint 2.2) |
| 7 | Gallery file/image security works | ✅ Satisfied (Sprint 2.2 + PR #7 remediation) |
| 8 | Availability management works | ✅ Satisfied (Sprint 2.4) |
| 9 | Availability concurrency is safe | ✅ Satisfied (Sprint 2.4 + PR #9 remediation, proven via `TransactionTestCase`) |
| 10 | Public profile composition is complete | ✅ Satisfied (Sprint 2.6 — redundant badge removed, SEO fixed) |
| 11 | Directory/search integration is consistent | ✅ Satisfied (BG-022, re-verified Sprint 2.6) |
| 12 | Public visibility is canonical | ✅ Satisfied (`common.is_publicly_visible_attrs()`, BG-022) |
| 13 | Caregiver dashboard works | ✅ Satisfied (Sprint 2.5) |
| 14 | Financial values use canonical sources | ✅ Satisfied (Sprint 2.5 — `WalletService`/`FinancialDocumentService`, no new calculation) |
| 15 | Private data remains private | ✅ Satisfied (Section 8/9 above; direct content-level proof added Sprint 2.6) |
| 16 | Owner mutation boundaries are enforced | ✅ Satisfied (every service re-verifies ownership per-row) |
| 17 | Query behavior is bounded | ✅ Satisfied except KL-012 (measured, quantified, documented — a pre-existing, shared-engine limitation, not a caregiver-profile defect) |
| 18 | Accessibility review is complete | ✅ Satisfied for caregiver-profile scope (Sprint 2.6) |
| 19 | Documentation is synchronized | ✅ Satisfied (Section 13) |
| 20 | Full tests are green | ✅ Satisfied (2082/2082) |
| 21 | No unresolved Phase 2 blocker remains | ✅ Satisfied — the only open item (bonus/penalty, KL-020) is an explicitly accepted external-domain dependency, not a profile-completion blocker |

**PHASE 2 (CAREGIVER PROFESSIONAL PROFILE) IS COMPLETE**, with the bonus/penalty
representation (KL-020) recorded as an accepted, explicitly-documented external-domain
dependency rather than a satisfied criterion in the strictest sense.

---

## 17. Recommended Next Phase

**Phase 3 — Company Portal** (per `IMPLEMENTATION_ROADMAP.md`): company staff management,
caregiver management, invitation system (company-initiated invite + join-by-code), approval/
removal, assignment management, company financial overview + reports, and company public
profile parity with the caregiver profile delivered in Phase 2 (gallery/certificates
generalized to organizations — including, if undertaken, a fix for the organization-profile
SEO bug recorded as KL-021/BG-027 during this sprint).

Before starting Phase 3, per this sprint's own governance: await review and merge of the
Sprint 2.6 PR; do not stack Phase 3 work on this unmerged branch.
