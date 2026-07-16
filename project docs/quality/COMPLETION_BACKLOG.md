# CURRENT GAPS AND COMPLETION BACKLOG

**Last verified HEAD:** phase1-verification-activation-rules (from main @ 278098b)
**Last verified date:** 2026-07-15

---

## P0 — Prevents Safe Continuation or Merge

### BG-001: Commit Phase 1 OrderOffer Implementation — **COMPLETE**

**Resolution:** OrderOffer model, migration `orders/0008_orderoffer.py`, tests,
and admin were committed in `ce3b30e` ("Repository documentation
reorganization"). Verified by `git log -- src/apps/orders/migrations/0008_orderoffer.py`
and clean working tree. Closed 2026-07-14.

### BG-002: Fix Pre-Existing Seed Test order_number Collision — **COMPLETE**

**Root cause:** Random in-run collision of the 4-digit suffix in
`orders/models.py:_generate_order_number()` (10,000 numbers/day); proven by a
1/10 isolated-run failure and two full-suite errors on 2026-07-14 at ce3b30e.
**Resolution (2026-07-14):** `Order.save()` now retries auto-generation up to
`ORDER_NUMBER_MAX_ATTEMPTS` (5) times when the database unique constraint
rejects a generated number, each attempt in its own savepoint; suffix widened
to 6 digits (10^6/day). Caller-supplied duplicates still raise immediately.
No migration required. Regression tests:
`orders/tests/test_order_number_generation.py` (8 tests incl. concurrency).
See CHANGE_LEDGER CL-017 and TEST_EXECUTION_LOG Run 009.
**MERGED to main** via PR #1, merge commit `eb51018` (2026-07-14), full
regression 1680/1680 green.

### BG-015: Manual Document Verification Workflow (Phase 1.1) — **COMPLETE (caregiver + organization)**

**Resolution (2026-07-15):** `VerificationReviewService` (approve/reject/request_correction,
row-locked, tenant-scoped, self-review refused, idempotent same-outcome
no-op, audited via `AuditLog`), `accounts.document.review` permission,
`DocumentStatus.CORRECTION_REQUIRED`, admin_portal review queue/detail/
file/review views, owner-facing reason display. 41 tests (25 service +
16 view). **MERGED to main** via PR #3, merge commit `278098b` (2026-07-15),
full regression 1721/1721 green at merge.
See traceability/IMPLEMENTATION_JOURNAL.md and ARCHITECTURE_DECISION_LOG ADM-014.
**Not included:** customer document verification (see BG-016), profile
verification_status roll-up (see BG-017 — now COMPLETE, see below).

---

## P1 — Blocks First Complete Internal Product Workflow

### BG-016: Customer Document Verification (Domain Model Gap)

**Current evidence:** `VerificationDocument.caregiver`/`.organization` are the only
two owner FKs (CHECK-constrained exactly-one-of-two); `CustomerProfile` has no
`verification_status` field. Confirmed by repository-wide inspection during
Phase 1.1 (2026-07-15) — customer identity verification does not exist as a
domain concept anywhere in the repository.
**Why needed:** Task governance for Registration & Verification names customer
identity verification as in-scope; current domain model does not support it.
**Dependencies:** A scoped decision on whether/how to extend `VerificationDocument`'s
owner CHECK constraint (a real architectural change, not a bug fix).
**Affected modules:** accounts
**Suggested implementation size:** Medium (new FK + constraint migration + service/view work)
**Risk:** Low-medium — additive to an existing, deliberately-designed constraint
**Not in scope:** Profile roll-up (BG-017)

### BG-017: Profile Verification Status Roll-Up — **COMPLETE**

**Resolution (2026-07-15, Phase 1.2):** `RequiredDocumentPolicy` (Part A —
the previously-missing policy: caregiver = IDENTITY + BACKGROUND_CHECK
required, organization = REGISTRATION + OPERATING_LICENSE required,
tenant-overridable via `ConfigResolver`, no migration) +
`ProfileVerificationRollupService` (Part B — derives the existing 4-value
`VerificationStatus` enum from required-document state; wired into
`VerificationReviewService`/`DocumentService.resubmit()`, never a view/
signal). Also delivered in the same slice: `DocumentService.resubmit()`
(Part C — owner-authorized correction/resubmission, blocks silent
replacement of a VERIFIED document) and `ActivationEligibilityService`
(Part D — read-only, structured eligibility for caregiver/organization).
47 new tests, zero new migrations. Branch
`phase1-verification-activation-rules`, PR pending merge. See
traceability/IMPLEMENTATION_JOURNAL.md and ARCHITECTURE_DECISION_LOG ADM-015.
**Not included:** wiring `ActivationEligibilityService` into an actual
activation/publishing action (currently read-only — see BG-018);
`profile_completion_percent` auto-recompute on every mutation (see BG-018).

### BG-018: Activation Wiring and Profile Completion Auto-Recompute — **COMPLETE**

**Resolution (2026-07-15, Phase 1.3):** `ProfileCompletionService` (Part A —
single source of truth for the base-profile-field checklist per profile
type; `calculate_caregiver_profile_completion()`/
`calculate_organization_profile_completion()` now delegate to it instead of
duplicating field lists — deterministic, called live on every read, no
persisted staleness to auto-recompute) and `ProfileActivationService`
(Part B/C — `activate_caregiver()`/`activate_organization()`, calls
`ActivationEligibilityService.evaluate()`, refuses when ineligible with
structured reasons, permission-gated via new `ACCOUNTS_PROFILE_ACTIVATE`,
row-locked, idempotent, audited). Minimum usable platform-operator and
owner-facing UI delivered (Part D). 40 new tests, zero new migrations.
Branch `phase1-activation-completion-final`, PR pending merge. See
`traceability/IMPLEMENTATION_JOURNAL.md` and `ARCHITECTURE_DECISION_LOG`
ADM-016.
**Not included:** automatic deactivation of an already-active profile when
verification later becomes invalid/expired (see BG-019 — no
suspension/revalidation workflow exists to hook it into).
**Remediated (2026-07-15, PR #5 review):** the initial implementation used
`AuditLog` existence, not `profile.status`, as the activation signal —
because registration left profiles `ACTIVE` by default, activation never
performed a real status transition in the common case. Fixed: caregiver/
organization registration now creates `ProfileStatus.DRAFT` profiles;
`ActivationEligibilityService` no longer requires `status == ACTIVE`
(removed the resulting circularity); `ProfileActivationService` now
performs a real `DRAFT -> ACTIVE` transition and judges idempotency from
`profile.status` directly. See `traceability/ARCHITECTURE_DECISION_LOG.md`
ADM-016's remediation note.

### BG-019: Automatic Deactivation on Verification Becoming Invalid/Expired

**Current evidence:** `ProfileActivationService` (BG-018/Phase 1.3) never
walks an already-ACTIVE profile's `status` back to a blocked state when its
verification later becomes invalid (e.g. a required document expires).
`ActivationEligibilityService.evaluate()` itself correctly reports
`eligible=False` again in that case (unchanged Phase 1.2 behavior) — only
the persisted `status` field is not automatically revised.
**Why needed:** Task governance for Phase 1.3 explicitly named this as an
acceptable deferral ("do NOT automatically deactivate an already-active
profile in this slice unless an explicit suspension/revalidation workflow
already exists") — recorded here rather than silently dropped.
**Dependencies:** A scoped decision on a suspension/revalidation workflow
(does not exist anywhere in the repository today).
**Affected modules:** accounts
**Suggested implementation size:** Medium (new workflow, likely a
scheduled job re-evaluating eligibility for ACTIVE profiles)
**Risk:** Medium — a real behavior change to already-active, customer-
facing profiles; needs its own product decision, not a guess
**Not in scope:** Marketplace visibility wiring (`is_publicly_visible()` is
a separate, existing, unrelated concern — see `traceability/IMPLEMENTATION_JOURNAL.md`)

### BG-020: Caregiver Professional Profile — Foundation Complete, Gallery/Financial/Orders Remain

**Resolution (2026-07-15, Phase 2.1):** `CaregiverSkill`/`CaregiverExperience` (new
models), `CaregiverSkillService`/`CaregiverExperienceService` (owner-authorized CRUD),
`PublicCredentialSelector` (safe public credential summary derived from approved,
unexpired `VerificationDocument` rows), corrected public-profile eligibility
(`verification_status == VERIFIED` + account `is_active`, added locally to
`CaregiverPublicProfileService.get_profile()`), provider-portal skill/experience
management pages, and public-profile skills/experience/credentials sections. Biography,
headline (`specialty`), services-offered (`ServiceSupplier.service_categories`), the
public profile route, and the provider-portal profile edit pages were already implemented
(Epic 06 Sprint 2) and reused, not rebuilt. 50 new tests, one new migration (2 new tables
only), full regression 1874/1874 green. Branch
`phase2-caregiver-professional-profile-foundation`, PR pending merge. See
`traceability/IMPLEMENTATION_JOURNAL.md` and `ARCHITECTURE_DECISION_LOG` ADM-017.
**Not included (roadmap Phase 2 remains open):** gallery (new model + upload service +
moderation flag), certificates-as-gallery presentation, extended financial overview,
orders + history pages — see BG-021.

### BG-021: Caregiver Profile — Gallery, Financial Overview, Orders + History — **Gallery portion RESOLVED**

**Original evidence:** Roadmap Phase 2's full scope (`IMPLEMENTATION_ROADMAP.md`) includes
an Instagram-like gallery, certificates surfaced as a visual gallery (distinct from
Phase 2.1's plain verified-credential badges), an extended financial/earnings overview,
and an orders + history page. None of these were implemented in Phase 2.1 — explicitly
out of that slice's scope per its own governance ("Do not implement: Instagram-style
gallery... caregiver financial dashboard... caregiver order dashboard...").
**Why needed:** Roadmap Phase 2 acceptance criteria are not met until these exist.
**Dependencies:** BG-020 (done — foundation this work builds on). Gallery specifically
also depends on the still-open media storage strategy for production (currently local
`FileField` — a pre-existing, acknowledged roadmap blocking item, still unresolved — Sprint
2.2 stores gallery images the same way avatar/cover already do, so it inherits, not
worsens, this open item).
**Affected modules:** accounts, provider_portal, public_site
**Suggested implementation size:** Medium-High (new GalleryItem model + upload/moderation
service; financial overview extension; orders/history read views)
**Risk:** Medium — new public-facing media upload surface; must not weaken the private/
public document boundary this and prior phases established
**Not in scope:** Marketplace offer workflow, invoice workflow, payment/settlement
changes (unrelated to gallery/financial-overview/orders-history display work)

**Resolution — gallery portion only (2026-07-15, Sprint 2.2):** `CaregiverGalleryItem`
(new model), `CaregiverGalleryService` (owner-authorized upload/edit/reorder/remove, row-
locked, Pillow-verified JPEG/PNG/WEBP, 5MB cap, 12-item cap), provider-portal gallery
management page, and a public-profile gallery section reusing the canonical BG-022
visibility policy (no second visibility rule). 45 new tests, one new migration (one new
table), full regression 1932/1932 green. See `traceability/IMPLEMENTATION_JOURNAL.md` and
`ARCHITECTURE_DECISION_LOG.md` ADM-018. Certificates-as-visual-gallery presentation
(distinct from Phase 2.1's plain badges) was explicitly out of Sprint 2.2's own scope
(Sprint 2.3's stated territory) and remains open. **Still open under BG-021:**
certificates-as-gallery presentation (Sprint 2.3), extended financial overview
(Sprint 2.5), orders + history (Sprint 2.5).

**Update (2026-07-15, Sprint 2.6):** Certificates-as-gallery presentation is superseded by
Sprint 2.3's precise verification-badge/highlights approach (a deliberate, documented
alternative to a visual certificate gallery, not an unaddressed gap — see ADM-019).
Dashboard-level financial overview and work/order summary were delivered by Sprint 2.5 and
finalized/integration-tested by Sprint 2.6 (`apps.public_site.tests.test_phase2_acceptance`)
— sufficient for Phase 2's own caregiver-public-profile acceptance criteria. Extended
financial reporting/exports and full orders-history pages remain genuinely open, but are
Company/Reporting-Portal-scale features explicitly outside both Sprint 2.5's and Sprint
2.6's mandates — not a Phase 2 profile-completion blocker. Phase 2 (Caregiver Professional
Profile) itself is accepted-complete; BG-021's remaining scope is recorded as future
roadmap work, not a Phase 2 defect.

### BG-022: Directory/Home-Page Listing Eligibility Does Not Match the Public Profile Page's Stricter Rule — **RESOLVED**

**Original evidence (Phase 2.1):** Phase 2.1 added `verification_status == VERIFIED` and
account `is_active` checks to `CaregiverPublicProfileService.get_profile()` (the single
caregiver profile page) only — deliberately not to the shared `apps.public_site.services
.common.is_publicly_visible()` function the caregiver directory (`directory_service.py`)
and home-page featured-caregiver listing (`home_service.py`) also call. A caregiver could
appear in directory/home-page listings while their own profile page 404'd (unverified or
inactive account).
**Original reasoning for deferring (Phase 2.1):** Consistency between "discoverable in a
listing" and "profile page loads" is a reasonable product expectation, though not one
Phase 2.1's own governance asked to fix — tightening it was judged out of that slice's
scope (see `ARCHITECTURE_DECISION_LOG.md` ADM-017 Decision 2 for the full original
reasoning, including that ~80 pre-existing directory/home-page tests appeared to depend on
the looser rule).
**Resolution (2026-07-15, PR #6 review):** governance explicitly overturned the deferral —
BG-022 was required to close inside PR #6, not be deferred further. Investigation found the
~80 "affected" pre-existing tests never actually asserted on `verification_status`; only
the shared test fixture's default needed to change (`verification_status="verified"` in
`apps/public_site/tests/helpers.py`). `apps.public_site.services.common
.is_publicly_visible_attrs()` is now the single canonical public-visibility rule (profile
`status == ACTIVE`, rolled-up `verification_status == "verified"`, account `is_active`,
active `OrganizationMembership` for org-affiliated caregivers), applied identically by the
detail page, directory search, and home-page listings. `CaregiverPublicProfileService
.get_profile()`'s now-redundant local duplicate check was removed.
`supplier_bridge.resolve_supplier_entities_bulk()` gained `select_related("user")`/
`select_related("admin_user")` — confirmed a JOIN on the existing batched query, adding
zero new queries (constant 2 queries regardless of candidate count). 13 new tests, full
regression 1887/1887 green. See `ARCHITECTURE_DECISION_LOG.md` ADM-017's second remediation
note and `traceability/IMPLEMENTATION_JOURNAL.md`.
**Affected modules:** public_site, accounts (supplier_bridge)
**Not in scope (found during remediation, tracked separately):** a pre-existing, unrelated
per-candidate N+1 in directory ranking/card-building (`DiscoveryRankingService.rank()`,
`CaregiverDirectoryService._build_card()`) — see `quality/DEFECT_AND_RISK_REGISTER.md`
KL-012. **Update (2026-07-15, Sprint 2.6 PR #11 remediation): KL-012 is now RESOLVED** —
batched via `CapacityService.bulk_is_capacity_exceeded()`, `resolve_supplier_entities_bulk()`
(reused in `SupplierSearchService`'s city filter), and new bulk rating/completed-jobs
methods; see `ARCHITECTURE_DECISION_LOG.md` ADM-022's remediation note.

### BG-023: Professional Credibility Layer — Precise Badges, Skill/Experience Visibility, Highlights — **RESOLVED**

**Original evidence:** Phase 2.1 delivered skills/experience CRUD and a plain-badge
credential summary, but left several gaps: `CaregiverSkill.is_visible`/
`CaregiverExperience.is_visible` existed on both models with no owner-facing way to change
either; the public profile showed one generic "تأییدشده" (Verified) badge regardless of
what was actually verified; no derived "highlights" summary existed anywhere; nothing
distinguished self-declared experience from platform-verified credentials in the UI; no
"credential expiring soon" state existed for the owner.
**Resolution (2026-07-15, Sprint 2.3):** `CaregiverSkillService.toggle_visibility()` and
`CaregiverExperienceService.create()`/`update()`'s new `is_visible` parameter close the
visibility gap (no migration — the column already existed). The single generic "Verified"
badge was replaced with precise, evidence-derived `VerificationBadgeViewModel` entries
("Profile verified", "Identity verified", "Professional credential verified") — never
implying broader approval than the underlying credential set supports. A fully derived
`ProfessionalHighlightsViewModel`/`HighlightsViewModel` (years of experience, verified-
credential count, visible-skill count, completed-jobs/review count) was added on both the
public profile and the provider-portal preview — zero new queries on the public side,
two new fixed-cost `.count()` queries on the provider side. The public experience section
gained an explicit "self-declared, not platform-verified" disclaimer, contrasted with a
matching "platform-reviewed" note on the credentials section.
`RequiredDocumentPolicy.is_expiring_soon()` (30-day window, owner-facing only, never
surfaced publicly) and `verification_badge.html`'s new `expiring_soon` status branch close
the last gap. 36 new tests, zero new migration, full regression 1984/1984 green. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-019 and
`traceability/IMPLEMENTATION_JOURNAL.md`.
**Affected modules:** accounts, provider_portal, public_site, plus the shared
`ui/components/portal/verification_badge.html` component (also used by
`organization_portal`; its own suite re-run to confirm no regression).
**Not in scope (explicitly deferred, not this sprint's mandate):** a skill catalog/
normalization layer (`CaregiverSkill.name` stays free-text — see
`quality/DEFECT_AND_RISK_REGISTER.md` KL-016); certificates-as-visual-gallery presentation
(distinct from this sprint's precise-badge/label treatment — remains open under BG-021);
availability/calendar (Sprint 2.4 — now RESOLVED, see BG-025); financial overview and
orders + history (Sprint 2.5).

### BG-024: Per-Caregiver Time Zone Not Modeled

**Evidence (2026-07-15, Sprint 2.4):** No per-tenant or per-caregiver time-zone field
exists anywhere in this repository (confirmed by grep before implementation). Every
availability evaluation (`AvailabilityQueryService.evaluate()`) resolves through Django's
default `timezone.localtime()`/`settings.TIME_ZONE` (`Asia/Tehran`) — the same single,
platform-wide source used everywhere else in the codebase. A caregiver physically located
in a different time zone would have their working windows interpreted against the platform
default, not their own local time.
**Why deferred:** Sprint 2.4's own governance explicitly instructed: "If caregiver-specific
time-zone is not modeled, use the existing tenant/platform time-zone and document the
limitation... Do not invent a second time-zone source." No evidence of demand for
multi-time-zone caregivers exists in this repository today (the product is Persian-first,
single-market).
**Resolution path (future):** Add an explicit `CaregiverProfile.time_zone` field (or a
tenant-level override) and thread it through `AvailabilityQueryService.evaluate()`'s
`timezone.localtime()` calls — a genuine, scoped follow-up once real multi-time-zone demand
exists.
**Affected modules:** availability, accounts (future).

### BG-025: Caregiver Availability and Working Schedule — **RESOLVED**

**Original evidence:** `apps.availability` (Module 10 foundation) already modeled weekly
working windows and time-off, and a basic provider-portal add/remove UI existed, but:
`add_working_window()` had no overlap/duplicate validation; there was no edit or
enable/disable UI for an existing window; `is_supplier_available()` returned a bare bool
with no explanation; and the public caregiver profile showed nothing about availability at
all.
**Resolution (2026-07-15, Sprint 2.4):** `AvailabilityMutationService` gained
duplicate/overlap refusal for active weekly windows and a `toggle_working_window()`
convenience method; the provider portal gained inline edit and enable/disable UI.
`AvailabilityQueryService.evaluate()` is now the one canonical, structured evaluator
(`available`, `reasons`, `matched_window`, `conflicting_blocked_period`, `timezone`) —
`is_supplier_available()` is a thin wrapper around it, zero behavior change for the
existing `apps.booking` consumer. The public caregiver profile gained a privacy-safe
schedule summary (weekday labels only, never exact times or time-off details), gated by
the same canonical `is_publicly_visible()` policy as every other public section; the
provider portal shows the identical computation as an owner-facing preview. 40 new tests,
zero new migration, full regression 2024/2024 green. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020 and
`traceability/IMPLEMENTATION_JOURNAL.md`.
**Affected modules:** availability, provider_portal, public_site.
**Not in scope (explicitly deferred, not this sprint's mandate):** per-caregiver time zone
(BG-024); overnight/midnight-spanning working windows (unchanged, pre-existing deferral);
booking/execution-session conflict awareness inside the evaluator (declined — see ADM-020
Decision 2); order matching/booking reservation/calendar sync/shift bidding/pricing/
invoices/payments/company workforce scheduling/customer scheduling UI (all explicitly out
of scope per this sprint's own governance).
**Concurrency remediation (2026-07-15, PR #9 review):** the overlap validation above was
found not concurrency-safe (unlocked check-then-insert); fixed by locking the owning
`ServiceSupplier` row before validation in both `add_working_window()`/
`update_working_window()`. 9 new `TransactionTestCase` tests. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020's remediation note.

### BG-026: Caregiver Professional Dashboard — **RESOLVED**

**Original evidence:** `apps.provider_portal.views.dashboard_view` already showed pending
assignments, active visits, `ProviderReportService` performance stats, reputation, and
notifications, but had no work summary broken out by status, no financial overview, no
wallet-movement visibility, no invoice summary, and no recent-reviews list — a caregiver
could not see a complete picture of their own current/upcoming/completed/cancelled work,
earnings, or invoices from one place.
**Resolution (2026-07-15, Sprint 2.5):** New `CaregiverDashboardPresentationService`
assembles five additional sections from entirely pre-existing, canonical selectors — work
summary (`Order.status`-derived current/upcoming/completed/cancelled counts and bounded
recent lists, via two new `OrderQueryService` methods), financial overview (existing
`WalletService`/`WalletTransactionService`), invoice summary (two new
`FinancialDocumentService` methods mirroring the existing customer-side selector), reviews/
reputation (existing `ReputationService.get_reputation_summary()` plus a new
`list_recent_reviews_with_reviewer_names()`), and professional statistics (reusing
`ProviderReportService` and Sprint 2.3's existing skill/credential/gallery-count
definitions). Bonus/penalty: confirmed no canonical representation exists anywhere in this
repository; documented as a gap rather than invented. 44 new tests, zero new migration, full
regression 2077/2077 green. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-021 and
`traceability/IMPLEMENTATION_JOURNAL.md`.
**Affected modules:** provider_portal, orders, finance, reviews.
**Not in scope (explicitly deferred, not this sprint's mandate):** new order/financial/
ledger/wallet/invoice/payment/settlement logic (all reused as-is); company dashboard;
customer dashboard; marketplace bidding; gallery/social changes; booking calendar changes;
payouts/withdrawals; accounting exports; bonus/penalty (no canonical model — recorded as a
new backlog item, see the "Deferred" note in `traceability/IMPLEMENTATION_JOURNAL.md`).

### BG-027: Organization Public Profile — SEO `page_url`/Canonical URL Bug

**Current evidence:** `templates/public_site/organization_profile.html` line 5 passes the
generic caregiver-directory-style URL `page_url="/find-an-organization/"` to
`ui/components/public/seo_meta.html` instead of the organization's own detail-page URL —
identical to the bug found and fixed on `caregiver_profile.html` during Sprint 2.6
(2026-07-15). This causes `og:url` (and any future `<link rel="canonical">`) for every
organization profile page to point at the directory listing instead of that organization's
own page.
**Why needed:** Correct Open Graph/canonical metadata per organization profile; social-share
previews and search engines currently cannot distinguish one organization's page from
another via this metadata.
**Affected modules:** public_site (organization profile template only).
**Suggested implementation size:** Trivial (one-line template fix, mirroring the caregiver
profile's Sprint 2.6 fix — resolve the organization's own detail URL via its named URL
pattern and pass it as both `page_url` and `canonical_url`).
**Required tests:** Existing organization-profile rendering tests; no new test infrastructure
needed.
**Risk:** Low — template-only, no behavior/privacy impact.
**Not in scope:** Any other organization-profile change. See `quality/DEFECT_AND_RISK_REGISTER.md`
KL-021.

### BG-028: Company-Caregiver Affiliation Foundation — **RESOLVED**

**Original evidence:** Roadmap Phase 3's first slice (`IMPLEMENTATION_ROADMAP.md`) needed a
complete company-caregiver affiliation lifecycle. Current-state inspection (Sprint 3.1,
2026-07-16) found the model layer already built (`OrganizationMembership`,
`CompanyAffiliationRequest`) but no path ever produced a PENDING membership, no invitation
concept existed, and zero UI/permission enforcement covered either model.
**Resolution (2026-07-16, Sprint 3.1):** Extended `apps.accounts.services.affiliations`
(not replaced) with the full lifecycle — join-by-code (tenant-scoped, exact-code,
ACTIVE-organization-only), company-initiated invitation, approval/rejection,
mutual termination (company-side permission-gated, caregiver-side ownership-authorized),
and read helpers for both portals. One migration (3 new nullable `OrganizationMembership`
termination fields — no new model). 4 new permission keys. New `organization_portal` staff-
page sections (pending requests/invitations, invite-by-phone, terminate) and a new
`provider_portal` "company" page. Every activation path locks the caregiver's own profile
row first, closing a genuine cross-organization race (proven by a new `TransactionTestCase`).
One active company per caregiver at a time is this sprint's documented minimal policy. 51 new
tests, full regression 2145/2145 green. See `traceability/ARCHITECTURE_DECISION_LOG.md`
ADM-023 and `traceability/IMPLEMENTATION_JOURNAL.md`.
**Affected modules:** accounts, organization_portal, provider_portal, kernel (permission keys).
**Not in scope (explicitly deferred, not this sprint's mandate):** company financial overview/
reports extension, company invoicing, company public profile parity with the caregiver
profile, company gallery/social feed, messaging, AI verification, payroll/salary, HR leave
workflow, caregiver scheduling by company, multi-company simultaneous affiliation.

### BG-029: No Flash-Message/Error-Surfacing Framework for Portal Action Views

**Current evidence:** `django.contrib.messages` is used nowhere in `apps.organization_portal`/
`apps.provider_portal`/`apps.portal` — confirmed by repository-wide inspection (Sprint 3.1,
2026-07-16). Every pure-POST action-button view (existing: `staff_approve_view`/
`staff_suspend_view`; new this sprint: the affiliation-lifecycle action views) silently
redirects back on failure with no visible feedback to the user.
**Why needed:** A caregiver/company admin whose action fails (e.g. a race-lost approval, an
invalid phone number) currently sees no indication anything went wrong — the page just
reloads unchanged.
**Affected modules:** organization_portal, provider_portal, portal (all three would need the
same framework).
**Suggested implementation size:** Medium (introduce `django.contrib.messages` framework-wide,
update every existing and new action view to surface a message, update every base template to
render them).
**Required tests:** New coverage for message rendering across all three portals.
**Risk:** Low — additive, no behavior change to the underlying actions themselves.
**Not in scope:** Sprint 3.1 deliberately matched the existing silent-redirect convention
rather than introducing flash messaging as a one-off. See `quality/DEFECT_AND_RISK_REGISTER.md`
KL-022.

### BG-003: OrderOfferService (Phase 2)

**Current evidence:** Phase 1 model exists. No service layer.
**Why needed:** Offer Marketplace cannot function without services to submit/edit/withdraw/select offers.
**Dependencies:** BG-001 (commit Phase 1)
**Affected modules:** orders
**Suggested implementation size:** Medium (1 service class + tests)
**Required tests:** Unit tests with PostgreSQL, concurrency tests
**Risk:** Medium — must not break existing assignment flow
**Not in scope:** Discovery, views, templates, APIs, payment integration

### BG-004: Implement Real PSP Adapter

**Current evidence:** Only `FakePaymentProviderAdapter` exists. All payment flows are mocked.
**Why needed:** Cannot process real payments without a real PSP.
**Affected modules:** payments
**Suggested implementation size:** Large (adapter + integration tests + configuration)
**Required tests:** Integration tests with sandbox PSP
**Risk:** High — financial correctness critical
**Not in scope:** Multiple PSP support, payment method diversity

### BG-005: Implement Real Notification Providers

**Current evidence:** Only fake SMS/email/push providers exist.
**Why needed:** Cannot send real notifications to users.
**Affected modules:** notifications
**Suggested implementation size:** Medium (per-provider adapter)
**Required tests:** Integration tests with sandbox providers
**Risk:** Medium — operational requirement
**Not in scope:** Multi-channel notification preferences

---

## P2 — Blocks External Pilot

### BG-006: Production Deployment Configuration

**Current evidence:** No docker-compose production config, no production settings beyond security headers.
**Why needed:** Cannot deploy to production.
**Affected modules:** config
**Suggested implementation size:** Medium
**Risk:** Medium
**Not in scope:** Kubernetes, auto-scaling

### BG-007: Enable Deadline Expiry Gate

**Current evidence:** `deadline_activation_enabled` defaults to DISABLED. Payment deadlines are created but don't auto-expire.
**Why needed:** Orders will remain in limbo if deadlines don't expire.
**Affected modules:** commission
**Suggested implementation size:** Small (config change + verification)
**Risk:** Medium — must verify expiry cascade works correctly
**Not in scope:** Deadline extension UI

### BG-008: Enable Pre-Service Payment Gate

**Current evidence:** `preservice_payment_enabled` defaults to DISABLED. No escrow hold before service.
**Why needed:** Financial protection for providers requires escrow.
**Affected modules:** commission, finance
**Suggested implementation size:** Medium (gate enablement + integration verification)
**Risk:** High — financial flow change
**Not in scope:** Customer payment UI

---

## P3 — Blocks Production Launch

### BG-009: Tenant Isolation Hardening

**Current evidence:** No middleware-level tenant injection. Depends on developer discipline.
**Why needed:** Cross-tenant data leak is the highest-severity security risk.
**Affected modules:** All
**Suggested implementation size:** Large (middleware + audit + row-level security)
**Risk:** High — architectural change
**Not in scope:** Multi-region deployment

### BG-010: CI Pipeline Activation

**Current evidence:** `.github/workflows/ci.yml` exists but never executed.
**Why needed:** No automated test execution on PRs.
**Affected modules:** DevOps
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Full CI/CD pipeline

### BG-011: RBAC Enforcement Audit Logging

**Current evidence:** No audit when `rbac.enforcement.enabled` is toggled.
**Why needed:** Security compliance.
**Affected modules:** kernel
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** RBAC redesign

---

## P4 — Post-Launch or Optimization

### BG-012: Remove Legacy Wallet from finance App

**Current evidence:** `finance.WalletAccount`/`WalletTransaction` superseded by `apps.wallet`.
**Why needed:** Reduce confusion.
**Affected modules:** finance
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Data migration

### BG-013: Add Tests for common App

**Current evidence:** Zero tests for shared utilities imported across apps.
**Why needed:** Regression protection for foundational code.
**Affected modules:** common
**Suggested implementation size:** Small
**Risk:** Low
**Not in scope:** Full coverage

### BG-014: Extract Shared Auth Guard

**Current evidence:** Each portal independently implements `_guard()`.
**Why needed:** DRY principle, single enforcement point.
**Affected modules:** All portals
**Suggested implementation size:** Medium
**Risk:** Low
**Not in scope:** Middleware redesign
