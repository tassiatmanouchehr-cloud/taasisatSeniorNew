# RUNTIME WORKFLOWS

**Last verified HEAD:** phase2-caregiver-public-profile-finalization (from main @ 9a26024, PR #10 merged)
**Last verified date:** 2026-07-15

---

## Workflow Implementation Status

| # | Workflow | Status | Key Entry Point |
|---|----------|--------|-----------------|
| 1 | Authentication (OTP) | IMPLEMENTED (fake SMS) | `accounts/views.py:verify_view` |
| 2 | Customer Registration | IMPLEMENTED | `accounts/services/registration_service.py` |
| 3 | Order Creation | IMPLEMENTED | `orders/services/order_creation.py:create_operator_order()` |
| 4 | Matching | IMPLEMENTED | `matching/services/match_orchestrator.py:run()` |
| 5 | Assignment | IMPLEMENTED | `booking/services/assignment_service.py:assign()` |
| 6 | Execution | IMPLEMENTED | `execution/services/session_service.py:create_session()` |
| 7 | Payment | MOCKED PSP | `payments/services/payment_intent_service.py:create_intent()` |
| 8 | Escrow | IMPLEMENTED | `finance/services/escrow_service.py:hold_for_order()` |
| 9 | Deadline | IMPLEMENTED (gated) | `commission/services/deadline_service.py:create_for_order()` |
| 10 | Dispute | IMPLEMENTED | `commission/services/dispute_service.py:open()` |
| 11 | Notifications | MOCKED providers | `notifications/services/dispatch_service.py:dispatch_pending()` |
| 12 | Wallet | IMPLEMENTED | `wallet/services/wallet_service.py` + `wallet_transaction_service.py` |
| 13 | Reviews | IMPLEMENTED | `reviews/services/review_submission_service.py` |
| 14 | Offer Marketplace | MODEL ONLY (Phase 1) | No service layer yet |
| 15 | Manual Document Verification (caregiver/organization) | IMPLEMENTED | `accounts/services/verification_review_service.py:VerificationReviewService` |
| 16 | Profile Verification Roll-up | IMPLEMENTED (Phase 1.2) | `accounts/services/verification_rollup_service.py:ProfileVerificationRollupService` |
| 17 | Document Resubmission (correction lifecycle) | IMPLEMENTED (Phase 1.2) | `accounts/services/document_service.py:DocumentService.resubmit()` |
| 18 | Activation Eligibility (read-only) | IMPLEMENTED (Phase 1.2) | `accounts/services/activation_eligibility_service.py:ActivationEligibilityService` |
| 19 | Profile Completion (deterministic) | IMPLEMENTED (Phase 1.3) | `accounts/services/profile_completion_service.py:ProfileCompletionService` |
| 20 | Controlled Profile Activation | IMPLEMENTED (Phase 1.3) | `accounts/services/profile_activation_service.py:ProfileActivationService` |
| 21 | Caregiver Skills Management | IMPLEMENTED (Phase 2.1; visibility toggle Sprint 2.3) | `accounts/services/caregiver_professional_profile_service.py:CaregiverSkillService` |
| 22 | Caregiver Experience Management | IMPLEMENTED (Phase 2.1; visibility toggle Sprint 2.3) | `accounts/services/caregiver_professional_profile_service.py:CaregiverExperienceService` |
| 23 | Public Credential Summary | IMPLEMENTED (Phase 2.1) | `accounts/services/public_credential_selector.py:PublicCredentialSelector` |
| 24 | Public Caregiver Profile Page | IMPLEMENTED (Epic 06; eligibility corrected Phase 2.1, unified with listings BG-022, gallery section Sprint 2.2, precise badges/highlights Sprint 2.3) | `public_site/services/profile_service.py:CaregiverPublicProfileService` |
| 25 | Canonical Public Visibility Policy | IMPLEMENTED (BG-022 remediation) | `public_site/services/common.py:is_publicly_visible_attrs()` |
| 26 | Caregiver Gallery Management | IMPLEMENTED (Sprint 2.2; file-lifecycle/image-safety hardened PR #7) | `accounts/services/caregiver_gallery_service.py:CaregiverGalleryService` |
| 27 | Professional Credibility Layer (badges, highlights, expiring-soon) | IMPLEMENTED (Sprint 2.3) | `public_site/services/profile_service.py:CaregiverPublicProfileService._highlights()/_verification_badges()` |
| 28 | Caregiver Availability and Working Schedule | IMPLEMENTED (Module 10 foundation; overlap validation, edit/toggle UI, canonical evaluator, public summary completed Sprint 2.4; concurrency-proven PR #9 review) | `availability/services/query_service.py:AvailabilityQueryService.evaluate()` |
| 29 | Caregiver Professional Dashboard | IMPLEMENTED (Sprint 2.5) | `provider_portal/services/dashboard_service.py:CaregiverDashboardPresentationService` |
| 30 | Public Profile Finalization and Phase 2 Acceptance | IMPLEMENTED (Sprint 2.6 + PR #11 KL-012 remediation — Phase 2 acceptance criteria satisfied except the accepted bonus/penalty dependency) | `public_site/services/profile_service.py:CaregiverPublicProfileService` (SEO/accessibility/redundant-badge fixes); `public_site/services/directory_service.py:CaregiverDirectoryService` (bulk card-data resolution); `discovery/services/ranking_service.py:DiscoveryRankingService` (bulk capacity check); `apps.public_site.tests.test_phase2_acceptance` (Phase 2 E2E acceptance + query-budget proof) |

---

## Manual Document Verification Workflow (Phase 1.1, extended Phase 1.2)

1. Caregiver/organization uploads a document via `DocumentService.upload_*_document()` — enters PENDING.
2. Platform reviewer (role `platform_owner`/`platform_admin`/`platform_support`, permission `accounts.document.review`) opens `/admin-portal/verification/documents/` (queue) and a document's detail page.
3. Reviewer approves, rejects (reason required), or requests correction (reason required) via `VerificationReviewService.approve()/reject()/request_correction()`.
4. Legal transitions: PENDING → {VERIFIED, REJECTED, CORRECTION_REQUIRED} only. Same-outcome repeat calls are idempotent no-ops; any other non-PENDING call raises a controlled `VerificationReviewError`. Row-locked (`select_for_update()`) so concurrent conflicting reviews leave exactly one winner.
5. Every review action is recorded in `AuditLog` (actor, before/after status, reason). The same transaction also syncs the owning profile's rolled-up `verification_status` (Phase 1.2, step 6 below).
6. Owner sees current status and (for REJECTED/CORRECTION_REQUIRED) the reviewer's reason on their own portal page — never on any public page.

## Correction and Resubmission Lifecycle (Phase 1.2)

1. Owner resubmits a REJECTED/CORRECTION_REQUIRED (or PENDING) document via `DocumentService.resubmit(document, actor=request.user, file=...)` — replaces `apps.provider_portal`/`apps.organization_portal`'s direct `replace_document()` call from Phase 1.1.
2. Refuses unless `actor` is the document's own owner user; refuses to touch an already-VERIFIED document (an owner can no longer silently discard a platform decision).
3. Resets status to PENDING (delegates to `replace_document()`'s existing file-swap mechanics), records an `accounts.document.resubmitted` `AuditLog` entry (the original review's reason remains permanently in its own, earlier `AuditLog` entry — never overwritten), and re-syncs the profile roll-up.
4. Row-locked — concurrent resubmissions of the same document serialize.

## Profile Verification Roll-up (Phase 1.2)

`ProfileVerificationRollupService.evaluate_caregiver()/evaluate_organization()` derives the existing `CaregiverProfile`/`OrganizationProfile.verification_status` (UNVERIFIED/PENDING/VERIFIED/REJECTED — no new value added) from `RequiredDocumentPolicy`'s required-document set for that profile type: any required document REJECTED → profile REJECTED; any required document CORRECTION_REQUIRED (none rejected) → profile PENDING with `needs_correction=True`; any required document missing/PENDING/effectively-expired → profile PENDING; all required documents VERIFIED and unexpired → profile VERIFIED. Optional document status never affects this. `sync_*()` persists the result (row-locked, idempotent no-op if unchanged) and is called automatically from `VerificationReviewService` and `DocumentService.resubmit()` — never from a view, admin action, or signal.

## Required-Document Policy (Phase 1.2)

`RequiredDocumentPolicy` (mandatory vs optional document types per profile type, tenant-overridable via the existing `ConfigResolver`): caregiver required = IDENTITY + BACKGROUND_CHECK (optional: QUALIFICATION, TRAINING_CERTIFICATE, LICENSE); organization required = REGISTRATION + OPERATING_LICENSE (optional: INSURANCE, PROFESSIONAL_PERMIT). No per-service variation (no repository infrastructure ties `ServiceCategory`/`ServiceType` to document requirements). Customer document verification and profile-level roll-up were explicitly deferred by Phase 1.1 — the roll-up gap is now closed by this phase; customer document verification remains deferred (no domain-model support exists — see `traceability/IMPLEMENTATION_JOURNAL.md` and `quality/COMPLETION_BACKLOG.md` BG-016).

## Activation Eligibility (Phase 1.2, read-only)

`ActivationEligibilityService.evaluate(profile)` returns a structured `eligible: bool` + `reasons: tuple[str, ...]` + the underlying `VerificationRollupResult`, for caregiver or organization. Eligible requires: profile `status == ACTIVE`, underlying `UserAccount.is_active`, base-profile completion at 100% (`calculate_caregiver_profile_completion()`/new `calculate_organization_profile_completion()`), and rolled-up `verification_status == VERIFIED`. Pure read, no side effects.

## Deterministic Profile Completion (Phase 1.3)

`ProfileCompletionService.evaluate_caregiver(profile)/evaluate_organization(profile)` is the single source of truth for the base-profile-field checklist per profile type (caregiver: display_name, phone, city, specialty, bio, years_experience, service_radius_km — 7 fields; organization: name, city, phone, address, description, company_type — 6 fields). Returns a frozen `ProfileCompletionResult(percent, completed, missing)` — deterministic and idempotent (no persisted state, recomputed live on every call). `0` in a numeric field (e.g. `years_experience=0`) counts as filled, not missing; blank string/`None` counts as missing. `calculate_caregiver_profile_completion()`/`calculate_organization_profile_completion()` in `profiles.py` delegate their percentage to this service (bare-int call signature unchanged for existing callers). Optional fields (anything not in the checklist) never block 100%.

## Controlled Profile Activation (Phase 1.3, corrected in the PR #5 remediation)

`ProfileActivationService.activate_caregiver(caregiver_id, *, tenant_id, actor)`/`activate_organization(organization_id, *, tenant_id, actor)` is the controlled, audited action that wires `ActivationEligibilityService` into a real effect. **`profile.status` is the sole source of truth for current activation state — `AuditLog` is historical evidence of the transition only, never consulted to determine current state** (the root defect the PR #5 remediation fixed: the original implementation used `AuditLog` existence as the activation signal, which never actually needed to transition `profile.status` because registration used to leave profiles `ACTIVE` by default).

1. Resolves and row-locks (`select_for_update()`) the profile inside `transaction.atomic`; a profile from another tenant is treated as not found.
2. Enforces `accounts.profile.activate` (`ACCOUNTS_PROFILE_ACTIVATE`, platform-scoped — granted to `platform_owner`/`platform_admin`/`platform_support` only) via `PermissionService.require()`.
3. Refuses self-activation (the acting `UserAccount` cannot be the profile's own owner), independent of RBAC grants.
4. If the profile is already `ACTIVE`, returns immediately with `transitioned=False` — an idempotent no-op, no eligibility re-check, no duplicate `AuditLog` entry.
5. Otherwise calls `ActivationEligibilityService.evaluate(profile)`; if ineligible, raises `ProfileActivationError` carrying the service's own structured reasons — no state change. `SUSPENDED`/`ARCHIVED` profiles are always ineligible this way (`ActivationEligibilityService` blocks those statuses outright).
6. If eligible: sets `status = ProfileStatus.ACTIVE` (a real `DRAFT -> ACTIVE` transition — registration now creates caregiver/organization profiles as `ProfileStatus.DRAFT`, not `ACTIVE`) and writes an `AuditLog` entry recording `before_snapshot`/`after_snapshot` status — the permanent record of *when* and *by whom* the transition happened, not the thing that determines current state. Returns a structured `ProfileActivationResult(profile, previous_status, status, transitioned=True)`.
7. Concurrent activation attempts on the same profile serialize via the row lock; exactly one real transition and one `AuditLog` entry result.
8. No automatic deactivation of an already-active profile is performed when verification later becomes invalid — recorded as a deferred item (`quality/COMPLETION_BACKLOG.md` BG-019); an already-`ACTIVE` profile stays activatable/idempotent even if a fresh eligibility check would now fail.

Platform side: `/admin-portal/verification/caregivers/<id>/` and `/admin-portal/verification/organizations/<id>/` (detail + blocking reasons) with a POST `/activate/` action, both permission-gated identically to the Phase 1.1 document-review views. The detail page shows a distinct "معلق" (Suspended) badge for a `SUSPENDED` profile rather than folding it into the generic ineligible case. Owner side: the provider/organization portal profile page shows one of four states — "فعال‌شده توسط پلتفرم" (activated, `profile.status == ACTIVE`), "پروفایل معلق شده است" (suspended), "آماده فعال‌سازی — در انتظار بررسی پلتفرم" (eligible DRAFT, awaiting platform action), or "هنوز آماده فعال‌سازی نیست" (ineligible DRAFT, with the blocking reasons listed) — via a reusable `ui/components/portal/activation_status.html` component, driven by `is_activated`/`eligible`/`profile_status` values the ViewModel derives from `profile.status` directly. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-016 (including its remediation note) for the full design rationale.

## Caregiver Professional Profile — Skills, Experience, Public Credential Summary (Phase 2.1)

`CaregiverSkillService.add_skill(caregiver, name=…)/remove_skill(caregiver, skill_id=…)/list_skills(caregiver)` — owner-authorized only (no RBAC permission key; ownership via `request.user.caregiver_profile` is the boundary). Duplicate names refused case-insensitively at the service layer, with a DB `UniqueConstraint` on `(caregiver, name)` as the concurrency backstop (a race between two identical concurrent submissions is caught as an `IntegrityError` and re-raised as the same controlled `AccountsError`).

`CaregiverExperienceService.create()/update()/delete()/list_experiences(caregiver)` — same ownership shape. `end_date` may be blank even when not current (no evidence to require it); `is_current=True` forces `end_date=None` server-side. A DB `CheckConstraint` (`end_date IS NULL OR end_date >= start_date`) backs the service-level date validation.

`PublicCredentialSelector.for_caregiver(caregiver)` — read-only. A `VerificationDocument` contributes to the public summary only if it is APPROVED (`DocumentStatus.VERIFIED`), not effectively expired (`RequiredDocumentPolicy.is_effectively_expired()`, reused from Phase 1.2), one of the caregiver-applicable document types (`CAREGIVER_APPLICABLE_DOCUMENT_TYPES`, reused from Phase 1.2), and owned by the queried caregiver. Returns a 3-field `PublicCredentialSummary` (document_type, label, expiry_date) — never file, document number, reviewer identity, or rejection/correction reason.

Public-profile eligibility (`CaregiverPublicProfileService.get_profile()`, `apps.public_site`) now also requires `verification_status == "verified"` and the owning account's `user.is_active`, added as a check local to the single-profile page — on top of, never replacing, the existing `common.is_publicly_visible()` (profile status ACTIVE + organization-membership-active, unchanged, still shared with the caregiver directory/home-page listings). See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017 for why this was added locally rather than in the shared function, and the resulting known gap (directory/home-page listings do not yet apply the same stricter rule).

**BG-022 remediation (2026-07-15, same PR #6):** the gap in the paragraph above is closed. `apps.public_site.services.common.is_publicly_visible_attrs()` is now the single canonical public-visibility rule — profile `status == ACTIVE`, rolled-up `verification_status == "verified"`, the owning account's own `is_active`, and (for org-affiliated caregivers) an active `OrganizationMembership`. Every public entry point calls this one function, directly or via `bulk_supplier_attrs()`/`supplier_entity_attrs()`: the detail page (`CaregiverPublicProfileService.get_profile()`, whose now-redundant local duplicate check was removed), directory search and featured listings, and the home-page featured cards/city filter (both go through the directory service). `apps.accounts.services.supplier_bridge.resolve_supplier_entities_bulk()` gained `select_related("user")`/`select_related("admin_user")` so the account's `is_active` is available from the same batched JOIN — no additional query, confirmed constant at 2 queries regardless of candidate count. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017's second remediation note and `quality/COMPLETION_BACKLOG.md` BG-022 (RESOLVED).

Caregiver-side management: `/provider/profile/skills/` (add/remove), `/provider/profile/experience/` (list), `/provider/profile/experience/add/`, `/provider/profile/experience/<id>/edit/`, `/provider/profile/experience/<id>/delete/` — all behind `_guard_with_caregiver()` plus a service-level `caregiver=caregiver` filter on every mutation (cross-caregiver/cross-tenant access returns 404, never a silent no-op). The provider profile page also shows a "which verified credential types will appear publicly" panel.

## Caregiver Gallery and Media Portfolio (Sprint 2.2)

`CaregiverGalleryService.add_item(caregiver, *, image, caption="", alt_text="")` —
validates caption/alt-text length (255 chars), then calls the shared
`apps.accounts.services.image_validation.validate_image()` (Pillow content-sniff, 5MB cap,
JPEG/PNG/WEBP — the identical function `ProfileMediaService` uses for avatar/cover, now
extracted into its own module so neither duplicates the check). Row-locks the owning
`CaregiverProfile` (`select_for_update()`) for the duration of a count-check-then-create so
two concurrent uploads cannot both bypass `MAX_GALLERY_ITEMS_PER_CAREGIVER = 12` (a fixed,
hardcoded cap — not tenant-configurable, no product requirement calls for that). New items
append at the next `display_order`.

`validate_image()` also bounds the **decoded** image, not just the uploaded byte size
(**remediation, PR #7 review, 2026-07-15**): `MAX_IMAGE_WIDTH`/`MAX_IMAGE_HEIGHT`/
`MAX_IMAGE_PIXELS` (8000px/8000px/25M px) are read from the image header immediately after
`Image.open()` — before any full pixel decode — and enforced ahead of that decode. A small,
adversarially-crafted file claiming an enormous decoded pixel grid ("decompression bomb")
is rejected by these explicit limits; Pillow's own `DecompressionBombError`/
`DecompressionBombWarning` are also caught (the warning promoted to a catchable exception
via a scoped filter) as defense-in-depth, both mapped to the same controlled
`AccountsError` — never an unhandled 500. Validation stays a single decode pass (open once,
read format/size, `verify()` once); the file stream is reset to position 0 afterward so the
subsequent `ImageField` save reads from the start.

`update_item(caregiver, *, item_id, caption, alt_text, is_visible)` — re-verifies
`caregiver=caregiver` in the same lookup that resolves the row; `is_visible` is the only
visibility lever short of permanent deletion (this model has no soft-delete/archive field —
see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-018 Decision 4 for why).

`reorder(caregiver, *, ordered_item_ids)` — row-locks the owning profile and every one of
its gallery items, then requires the id list to be exactly the caregiver's own items, each
exactly once; any foreign/missing/duplicate id refuses the whole operation, never a partial
reorder. The provider-portal UI exposes this as simple "move up"/"move down" buttons per
item (plain POST forms, no JS drag-and-drop dependency), computing the swapped order before
calling `reorder()`.

`remove_item(caregiver, *, item_id)` — row-locks the target item, deletes the database row,
then schedules physical file deletion via `transaction.on_commit()` — never inline, and
never before the row is gone. **Remediation (PR #7 review, 2026-07-15):** the original
implementation deleted the physical file first and the row second, inside the same
transaction; since filesystem operations don't participate in a database transaction, a
later rollback of that transaction would have left a live row pointing at an
already-deleted file. Now the order is reversed and the file deletion is deferred to
post-commit — if the transaction rolls back, Django discards the scheduled callback
entirely and the file is never touched; if the file deletion itself later fails, the
failure is logged (`_delete_stored_file()`), never raised — the row is already committed
gone either way, so the only possible outcome is a detectable orphaned file, never a
resurrected row or a broken request. Orphan-file cleanup/retry is explicitly deferred (no
cleanup-job infrastructure exists in this repository). Removing a gallery item never
touches `avatar`/`cover_image` (three distinct responsibilities, never conflated). See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-018's remediation note.

Public exposure: `CaregiverPublicProfileService._gallery()` adds no eligibility check of
its own — it only runs after `get_profile()`'s existing canonical
`common.is_publicly_visible(supplier)` gate (BG-022) has already passed, then filters to
`caregiver.gallery_items.filter(is_visible=True)`, the identical per-item pattern
`_skills()`/`_experience()` already established. A caregiver failing the canonical policy
(DRAFT/SUSPENDED/ARCHIVED/unverified/pending-verification/inactive-account/inactive-
membership) never has their gallery resolved at all.

Caregiver-side management: `/provider/profile/gallery/` (list + upload),
`/provider/profile/gallery/<id>/edit/` (caption/alt-text/visibility),
`/provider/profile/gallery/<id>/remove/`, `/provider/profile/gallery/<id>/move/<up|down>/`
— all behind `_guard_with_caregiver()` plus the same `caregiver=caregiver` ownership
filter. The provider profile page shows a gallery summary tile ("N / 12 تصویر ثبت‌شده").
The public profile page shows a responsive photo grid, only when both the caregiver passes
the canonical visibility policy and the item itself is `is_visible=True`.

## Professional Credibility Layer — Badges, Highlights, Visibility Management (Sprint 2.3)

Skill/experience visibility: `CaregiverSkillService.toggle_visibility(caregiver, *,
skill_id)` flips `is_visible` (ownership-filtered, same lookup-as-authorization-boundary
pattern as every other mutation in this service). `CaregiverExperienceService.create()`/
`update()` gained an `is_visible: bool = True` keyword parameter, wired to a new checkbox
on `ExperienceForm`. Both columns existed on their models since Phase 2.1; this sprint is
the first to expose either through a mutation path. Provider portal: a "نمایش/پنهان کردن"
toggle button per skill row (`/provider/profile/skills/<id>/toggle-visibility/`, new
POST-only route), and the existing experience edit form.

Public precise badges: `CaregiverPublicProfileService._verification_badges(attrs,
credentials)` replaces the old single generic "Verified" pill with independently
evidence-derived `VerificationBadgeViewModel` entries — "نمایه تأییدشده" (profile passed
the canonical BG-022 gate), "هویت تأییدشده" (an approved, unexpired IDENTITY document
exists), "مدرک حرفه‌ای تأییدشده" (at least one approved credential of any applicable type
exists). Never a single badge implying broader approval than the underlying evidence.

Highlights: `_highlights()` (public) and `ProviderProfilePresentationService._highlights()`
(owner preview) are both pure aggregations of data already resolved elsewhere on the same
page (years of experience, verified-credential count, visible-skill count, completed-jobs/
review count) — the public version adds zero new queries; the owner version adds two
fixed-cost `.count()` queries (`WHERE is_visible`, distinct from the pre-existing
unfiltered `skills_count`/`experience_count`).

Expiring-soon (owner-facing only, never public): `RequiredDocumentPolicy
.is_expiring_soon()` — a VERIFIED document whose `expiry_date` falls within the next 30
days. Surfaced via a new `expiring_soon` branch on the shared
`ui/components/portal/verification_badge.html` component (also used by
`apps.organization_portal` — its own suite re-run to confirm no regression from the
purely-additive change).

Self-declared vs. platform-verified: the public experience section carries an explicit
"این سوابق توسط خود مراقب اعلام شده و توسط پلتفرم تأیید نشده است." disclaimer (no
experience-verification record exists to derive a stronger claim from); the credentials
section carries a contrasting "این مدارک توسط پلتفرم بررسی و تأیید شده‌اند." note.

No new eligibility/visibility rule was introduced — badges and highlights are only ever
computed after `get_profile()`'s existing canonical `common.is_publicly_visible()` gate
(BG-022) has already passed, exactly like every other section on this page.

## Caregiver Availability and Working Schedule (Sprint 2.4)

`apps.availability` (Module 10 foundation) already owned the domain model
(`ProviderWorkingWindow`, `AvailabilityBlockedPeriod`, both keyed on `kernel.ServiceSupplier`)
and a basic add/remove UI before this sprint; this sprint completed it.

Weekly schedule: `AvailabilityMutationService.add_working_window()`/`update_working_window()`
now refuse a duplicate or overlapping *active* window on the same day for the same supplier
(`_validate_no_overlap()`) — a disabled window is excluded from the check on both sides, so
re-enabling one, or adding a new window over its old slot, still works. Provider portal:
add (existing), inline edit (new — `working_window_update_view`), enable/disable toggle
(new — `working_window_toggle_view`, mirrors Sprint 2.3's skill-visibility-toggle pattern),
remove (existing).

**Concurrency (PR #9 review, 2026-07-15):** the overlap check above is only correct if two
concurrent mutations against the same supplier's schedule cannot both read "no conflict"
before either commits. `add_working_window()` and `update_working_window()` both now lock
the owning `kernel.ServiceSupplier` row (`select_for_update()`) as the first statement inside
their transaction, before running `_validate_no_overlap()` — so two concurrent creates,
updates, or enable-toggles against the same supplier always serialize, and the loser sees the
winner's already-committed state. `toggle_working_window()` inherits this automatically
(it delegates to `update_working_window()`). Different suppliers never contend for the same
lock. Proven by 9 `TransactionTestCase` tests in `apps.availability.tests.test_concurrency`.
See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020's remediation note.

Time-off: unchanged from Module 10 foundation — `AvailabilityMutationService
.add_blocked_period()`/`remove_blocked_period()`, no cancelled/active state (hard delete is
the existing, kept convention). Overlapping blocked periods are deliberately still allowed
to coexist (pre-existing, tested behavior — harmless redundant unavailability, not a
conflict; see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020 Decision 3).

Canonical evaluator: `AvailabilityQueryService.evaluate(*, supplier, start, end)` returns a
structured, frozen `AvailabilityEvaluation` (`available`, `reasons`, `matched_window`,
`conflicting_blocked_period`, `timezone`) — read-only, never mutates. `is_supplier_available()`
is now a thin bool-only wrapper around it (zero behavior change for the existing booking
consumer, `apps.booking.services.assignment_service`). Deliberately stays supplier-keyed,
not caregiver-keyed — see ADM-020 Decision 1 for why a caregiver-shaped entry point was not
added.

Public availability summary: `CaregiverPublicProfileService._schedule_summary()` shows only
which weekdays have at least one active working window (`AvailabilityScheduleSummaryViewModel
.available_day_labels`, Persian day names from the new canonical
`apps.availability.models.PERSIAN_DAY_LABELS`) — never exact times, never anything about
time-off. Gated by the same canonical `common.is_publicly_visible()` policy as every other
section; adds one fixed-cost query (`get_distinct_active_days()`), proven O(1) by the
existing gallery-item-count-scaling query test. The provider-portal availability page shows
the identical summary as an owner-facing preview of what the public sees.

Time zone: no per-caregiver or per-tenant time-zone field exists anywhere in this
repository; every evaluation resolves through Django's default `timezone.localtime()`/
`settings.TIME_ZONE` (`Asia/Tehran`) — documented as a known platform-wide-only limitation,
not fixed (see ADM-020 Decision 5).

## Caregiver Professional Dashboard (Sprint 2.5)

`apps.provider_portal.views.dashboard_view` already showed pending assignments, active
visits, `ProviderReportService` performance stats, reputation, and notifications before this
sprint; this sprint completed it with five additional, purely read-only sections, assembled
by the new `apps.provider_portal.services.dashboard_service
.CaregiverDashboardPresentationService` into a single `dashboard` context variable (see
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-021 for the full read-model decision).

Work summary: `Order.status`-derived counts (current = IN_PROGRESS, upcoming =
WAITING_SERVICE, completed = COMPLETED, cancelled = CANCELLED — no new statuses invented),
via two new methods on the existing `apps.orders.services.queries.OrderQueryService`:
`list_for_supplier()` (mirrors `list_for_customer()`) and `count_by_status_for_supplier()`
(one aggregate query). Bounded to 5 recent items per tab.

Financial overview: reuses `apps.wallet.services.wallet_service.WalletService
.get_wallet_or_none()` and `apps.wallet.services.wallet_transaction_service
.WalletTransactionService.list_transactions()` (both pre-existing) for the balance and the
10 most recent movements — no new financial calculation. Bonus/penalty: no canonical
representation exists anywhere in this repository (confirmed by inspection); rather than
invent one, `FinancialOverviewViewModel.bonus_penalty_note` documents the gap directly, and
the recent-movements list already shows every CREDIT/DEBIT/ADJUSTMENT regardless of category
(see ADM-021 Decision 4).

Invoice summary: new `apps.finance.services.document_service.FinancialDocumentService
.list_for_beneficiary_party()`/`count_by_status_for_beneficiary_party()`, mirroring the
existing `list_for_payer_party()` (the customer/payer side of the same `FinancialDocument`
model, already used by `apps.portal`) — filtered by the document's other existing party
column, `beneficiary_party`, never a new financial-document query path.

Reviews/reputation: `ReputationService.get_reputation_summary()` (pre-existing, unchanged)
plus a new `list_recent_reviews_with_reviewer_names()` — APPROVED-only, reviewer-name
resolved the same way `apps.public_site`'s public profile already does it, kept inside
`apps.reviews` so `apps.provider_portal/views.py` never queries `Review`/`Person` directly.

Professional statistics: `completed_jobs`/`active_assignments` reuse
`ProviderReportService.get_report_for_supplier()` unchanged (a CLOSED-`ExecutionSession`
definition, deliberately kept distinct from the work summary's Order-status-based
`completed_count` — see ADM-021 Decision 3); `cancelled_orders` reuses the work summary's
own count; `average_rating` reuses the same `ReputationSnapshot.average_score` every other
page reads; `verified_credential_count`/`visible_skill_count`/`visible_gallery_item_count`
reuse the exact definitions Sprint 2.3's public highlights already established.

Zero new models, zero new migrations. `apps.provider_portal/views.py` gains zero new direct
model/ORM references — all new data-gathering lives in
`CaregiverDashboardPresentationService.build_for_supplier()`.

## Public Profile Finalization and Phase 2 Acceptance (Sprint 2.6)

No new workflow — this sprint finalizes the existing public caregiver-profile workflow
(items 21-29 above) as one coherent, accepted capability, fixing integration/quality/
accessibility/SEO defects found while proving each Phase 2 acceptance criterion end to end.
See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-022 and `project docs
/PHASE_2_COMPLETION_REPORT.md` for the full record. In summary:

- The caregiver public profile page (`public_site/services/profile_service.py
  :CaregiverPublicProfileService`) now passes its own URL (not the directory's) to the
  shared SEO component, and no longer renders a second, always-true generic verification
  badge alongside the precise Sprint 2.3 badges.
- Four `provider_portal` templates gained proper `<label for=...>` association and a
  non-empty `alt` fallback on gallery images.
- The directory/search/home/detail-page canonical visibility policy (workflow #25, BG-022)
  and the provider "public preview" link (a direct link to the real public URL, not a
  separate render path) were both re-verified, not changed.
- New end-to-end acceptance coverage
  (`apps.public_site.tests.test_phase2_acceptance.Phase2FullLifecycleAcceptanceTest`) drives
  a caregiver from DRAFT through activation, editable-field changes, mixed-visibility
  skills/experience/gallery, weekly availability, and credential approval, then verifies the
  public profile page, directory, search, and home all compose the result correctly, and
  that a second, ineligible caregiver appears nowhere.

### PR #11 Review Remediation — Resolve the KL-012 Query-Performance Blocker

A subsequent architecture review of PR #11 found the directory/home query-count measurement
above inconsistent with Phase 2's own "query behavior is bounded" acceptance criterion: the
counts genuinely scaled with total matching-candidate count, not page size. Root cause: three
independent per-candidate query calls — `DiscoveryRankingService._score()`'s per-candidate
`CapacityService.is_capacity_exceeded()` call inside `rank()`'s scoring loop;
`SupplierSearchService.filter_suppliers()`'s per-candidate `resolve_supplier_entity()` call
inside its city filter; and `CaregiverDirectoryService._build_card()`'s per-built-card
`rating_summary()`/`completed_jobs_count()` calls. Fixed by batching each at its own
canonical selector boundary: `CapacityService.bulk_is_capacity_exceeded()` (new,
`apps.availability`), the pre-existing `resolve_supplier_entities_bulk()` (built for exactly
this class of problem during Epic 06's Architecture Review remediation M1), and two new bulk
methods (`ReputationService.get_reputation_summaries_bulk()`,
`common.completed_jobs_counts_bulk()`/`rating_summaries_bulk()`). Ranking formula, scoring
weights, sort order, filter semantics, and public-visibility policy are all unchanged —
proven by the pre-existing `apps.discovery`/`apps.availability`/`apps.reviews` suites passing
unmodified. Directory/search/home query counts are now fully flat (16/17/17 respectively)
from 1 through 100+ matching candidates. See `traceability/ARCHITECTURE_DECISION_LOG.md`
ADM-022's remediation note.

## Order Lifecycle (Status Machine)

```
NEW ──→ WAITING_SERVICE ──→ IN_PROGRESS ──→ COMPLETED
  ↑           │                    │
  │           ↓                    ↓
  │      CANCELLED            CANCELLED
  │
  └── (reopen on assignment expiry)

PUBLIC orders: PENDING_OPERATOR_REVIEW → NEW → ...
```

Status transitions are managed exclusively by `apps/orders/services/status_machine.py`. No other service mutates `Order.status` directly.

## Assignment → Financial Core Flow

When `AssignmentService.assign()` is called:

1. `Order.select_for_update()` — row lock
2. Tenant check
3. Permission check (`BOOKING_ASSIGNMENT_ASSIGN`)
4. Optional availability/capacity validation (gated)
5. `status_machine.assign_supplier()` → Order.status = WAITING_SERVICE
6. Create `SupplierAssignment` row
7. Mark `MatchCandidate` as SELECTED
8. Publish `Booking.Assignment.Created.v1` event
9. Publish `ORDER_ASSIGNED` domain event
10. `CommissionSnapshotService.create_snapshot_for_order()` — freeze commission policy
11. `PaymentDeadlineService.create_for_order()` — create deadline (optionally schedule expiry job)
12. `PreServicePaymentService.create_invoice_and_intent_for_order()` — gated, disabled by default

## Escrow Lifecycle

```
                     ┌─── hold_for_order() ───→ HELD
                     │
                     ├─── mark_releasable() ──→ moves remaining → releasable
                     │
                     ├─── block_for_dispute() → moves remaining → blocked
                     │
    HELD ────────────├─── unblock() ─────────→ moves blocked → remaining
                     │
                     ├─── apply_release() ────→ PARTIALLY_RELEASED → FULLY_RELEASED → CLOSED
                     │
                     └─── apply_refund() ─────→ PARTIALLY_REFUNDED → FULLY_REFUNDED → CLOSED
```

Conservation equation: `original_amount = held + remaining + releasable + blocked + released + refunded`

## Dispute Flow

1. Customer calls `DisputeService.open()` with disputed_amount and lines
2. Validates: feature gate, authorization (must be order customer), escrow state, amount bounds
3. Creates `Dispute` + `DisputeLine` rows
4. Calls `EscrowService.block_for_dispute()` — moves disputed amount from remaining to blocked
5. Transitions `ObjectionPeriod` to DISPUTED (if exists)

Resolution:
1. Admin calls `DisputeResolutionService.resolve()` with allocation (customer_refund + platform + company + caregiver)
2. Validates allocation sums to disputed amount
3. Creates `DisputeResolution` row
4. Calls `EscrowService.unblock()` — returns blocked to remaining
5. Creates `RefundInstruction` → `EscrowService.apply_refund()`
6. Creates `ReleaseInstruction` → `EscrowService.apply_release()`

## Deadline Expiry Flow

1. `PaymentDeadlineService.expire_due()` (scheduled job handler)
2. Row lock on deadline, idempotent check
3. Safety gate re-check: `deadline_activation_enabled` (DISABLED by default)
4. Transitions deadline to EXPIRED
5. Calls `AssignmentService.expire()`:
   - `status_machine.remove_supplier()` → Order goes back to NEW
   - Marks SupplierAssignment as EXPIRED
   - Publishes `Booking.Assignment.Expired.v1`

**Key insight**: The full cascade is implemented but gated. PaymentDeadline rows are created (data foundation) but expiry jobs are not scheduled unless gate is enabled.
