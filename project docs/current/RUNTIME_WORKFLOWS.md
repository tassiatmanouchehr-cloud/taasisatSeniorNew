# RUNTIME WORKFLOWS

**Last verified HEAD:** phase2-caregiver-professional-profile-foundation (from main @ 0c9d70c, PR #5 merged; PR #6 BG-022 remediation in progress)
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
| 21 | Caregiver Skills Management | IMPLEMENTED (Phase 2.1) | `accounts/services/caregiver_professional_profile_service.py:CaregiverSkillService` |
| 22 | Caregiver Experience Management | IMPLEMENTED (Phase 2.1) | `accounts/services/caregiver_professional_profile_service.py:CaregiverExperienceService` |
| 23 | Public Credential Summary | IMPLEMENTED (Phase 2.1) | `accounts/services/public_credential_selector.py:PublicCredentialSelector` |
| 24 | Public Caregiver Profile Page | IMPLEMENTED (Epic 06; eligibility corrected Phase 2.1, unified with listings BG-022) | `public_site/services/profile_service.py:CaregiverPublicProfileService` |
| 25 | Canonical Public Visibility Policy | IMPLEMENTED (BG-022 remediation) | `public_site/services/common.py:is_publicly_visible_attrs()` |

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
