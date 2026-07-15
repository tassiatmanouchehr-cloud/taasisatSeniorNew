# ARCHITECTURE DECISION LOG

**Repository:** taasisatSenior
**Scope:** Offer Marketplace epic decisions only
**Policy:** Each decision is recorded once, with status tracking

---

## ADM-001: OrderOffer.SELECTED Represents the Temporary Hold

```
Decision ID: ADM-001
Context: The marketplace golden flow requires a 30-minute hold after customer selection.
         First draft proposed a separate reservation table.
Decision: OrderOffer.SELECTED status IS the temporary hold. No separate reservation model.
Alternatives considered:
  A. Separate Reservation model (rejected — unnecessary complexity, OrderOffer already carries all needed data)
  B. SupplierAssignment.PROPOSED as hold (rejected — wrong semantic, allows provider confirm/decline during hold)
  C. New field on Order model (rejected — Order should not carry offer lifecycle state)
Reason: OrderOffer already has status, hold_expires_at, selected_at fields. Adding a separate table duplicates data and creates synchronization risk.
Affected code: None yet (contract phase)
Risks: None — simplifies the design
Status: Accepted
```

## ADM-002: SupplierAssignment Created Only After Payment Success

```
Decision ID: ADM-002
Context: The marketplace golden flow requires assignment timing decision.
         Option A: at offer selection before payment; Option B: only after successful payment.
Decision: Option B — SupplierAssignment is created only after successful payment.
Alternatives considered:
  A. Create at selection (rejected — premature side effects: status change, capacity reduction, notification, provider actions)
  B. Create after payment (accepted — clean financial flow, no premature mutations)
Reason: Tracing every side effect of AssignmentService.assign() shows 10+ downstream effects that would fire prematurely if called at selection time.
Affected code: OrderOfferService.select_offer() does NOT call AssignmentService.assign(). Payment success wiring calls confirm_payment() which calls assign().
Risks: Order stays NEW during hold — caregivers may see it as available (addressed by ADM-003)
Status: Accepted
```

## ADM-003: Order Hidden from Marketplace During Active Hold

```
Decision ID: ADM-003
Context: Order stays NEW during hold (ADM-002), but should not appear as freely available.
Decision: Marketplace discovery query adds guard: no OrderOffer with status=SELECTED exists for the order.
Alternatives considered:
  A. Change Order status to HOLDING (rejected — adds complexity, breaks "order must be NEW" invariant)
  B. Hide via discovery query guard (accepted — minimal change, preserves Order status semantics)
  C. Add a boolean flag on Order (rejected — denormalized, synchronization risk)
Reason: The guard is a single WHERE clause addition to the discovery query. Order status remains NEW, which is semantically correct (the order IS still open, just temporarily reserved).
Affected code: OrderDiscoveryService.query(), offer submission guard
Risks: None — the guard is idempotent and atomic
Status: Accepted
```

## ADM-004: Selection Policy — One Active Hold Per Order

```
Decision ID: ADM-004
Context: Customer may attempt to select multiple offers. Need unambiguous policy.
Decision: Selecting a different offer while a hold is active is REJECTED. Customer must wait for expiry or cancel.
Alternatives considered:
  A. Replace old selection with new (rejected — complex state management, old offer's payment flow unclear)
  B. Reject new selection (accepted — simple, predictable, matches real-world UX)
  C. Queue new selection (rejected — over-engineered for initial implementation)
Reason: Simplicity and predictability. Customer sees clear error message. No complex rollback needed.
Affected code: OrderOfferService.select_offer() checks for existing SELECTED offer
Risks: Customer may be frustrated if hold is long — mitigated by 30-minute limit
Status: Accepted
```

## ADM-005: Payment Failure Does NOT Expire the Hold

```
Decision ID: ADM-005
Context: Payment may fail during the 30-minute hold. Need to define behavior.
Decision: Payment failure leaves the hold active. Customer may retry.
Alternatives considered:
  A. Expire on failure (rejected — punitive, customer may retry immediately)
  B. Leave hold active (accepted — customer-centric, allows retry)
  C. Reduce hold time on failure (rejected — complex, no clear benefit)
Reason: Real-world payment failures are often transient (network timeout, insufficient funds). Customer should be able to retry without losing the hold.
Affected code: PaymentCallbackService — FAILED status does not trigger any offer state change
Risks: Hold time continues counting down during retries — customer must succeed within 30 minutes total
Status: Accepted
```

## ADM-006: Ownership Enforced Inside Service Methods

```
Decision ID: ADM-006
Context: Authorization was previously portal-view-only. Need defense in depth.
Decision: All service methods enforce ownership and tenant checks internally.
Alternatives considered:
  A. View-only authorization (rejected — API callers bypass views)
  B. Service-level enforcement (accepted — defense in depth)
  C. Middleware-level enforcement (rejected — too coarse, doesn't know business context)
Reason: API endpoints and future integrations may bypass portal views. Service-level checks ensure no unauthorized access regardless of entry point.
Affected code: All OrderOfferService methods
Risks: Slight performance overhead from additional queries — acceptable for correctness
Status: Accepted
```

## ADM-007: PostgreSQL Required for Transaction and Constraint Tests

```
Decision ID: ADM-007
Context: SQLite cannot test UniqueConstraint conditions, select_for_update, or concurrent transactions.
Decision: All service, transaction, constraint, and concurrency tests must use PostgreSQL.
Alternatives considered:
  A. SQLite for unit tests (rejected — cannot test constraints, locking, or concurrency)
  B. PostgreSQL for all tests (accepted — matches production, tests real behavior)
  C. Mock database (rejected — does not test real ORM behavior)
Reason: The repository's existing test suite uses PostgreSQL. UniqueConstraint conditions and select_for_update are PostgreSQL-specific features that SQLite does not support.
Affected code: Test configuration (DATABASE_ENGINE=django.db.backends.postgresql)
Risks: Tests require running PostgreSQL — documented requirement
Status: Accepted
```

## ADM-008: Existing Operator-Assignment Flow Must Remain Functional

```
Decision ID: ADM-008
Context: The offer flow is an alternative to operator-assignment, not a replacement.
Decision: The existing matching→operator-assign flow continues to work unchanged.
Alternatives considered:
  A. Replace operator-assignment with offer flow (rejected — breaking change)
  B. Keep both flows (accepted — additive change)
  C. Deprecate operator-assignment (rejected — out of scope)
Reason: Existing customers and operators use the current flow. The offer flow is a new capability, not a replacement.
Affected code: None — existing AssignmentService.assign() is called unchanged at payment time
Risks: Two parallel flows may confuse users — mitigated by clear UI separation
Status: Accepted
```

## ADM-009: Real PSP, SMS, PR-C, and Production Integration Outside Scope

```
Decision ID: ADM-009
Context: The Offer Marketplace epic should not attempt to add real external integrations.
Decision: Real PSP, SMS, PR-C (release instruction consumption), and production deployment remain outside this epic.
Alternatives considered:
  A. Include real PSP (rejected — massive scope expansion, separate workstream)
  B. Include PR-C (rejected — separate epic with its own dependencies)
  C. Keep epic focused (accepted — deliverable increment)
Reason: The Offer Marketplace is a UI and workflow layer. Real integrations are separate workstreams with their own timelines and risks.
Affected code: None — FakePaymentProviderAdapter continues to be used for testing
Risks: E2E tests use fake providers — documented limitation
Status: Accepted
```

## ADM-010: Money Representation — DecimalField(14,2)

```
Decision ID: ADM-010
Context: Repository has two money representations: DecimalField(14,2) and integer IRR.
Decision: OrderOffer uses DecimalField(max_digits=14, decimal_places=2), matching Quote, FinancialDocument, PaymentIntent, Wallet.
Alternatives considered:
  A. Integer IRR (rejected — used only in EscrowRecord PR-B fields and AllocationCalculator, not customer-facing)
  B. DecimalField(14,2) (accepted — canonical representation across 49 usages in codebase)
  C. FloatField (rejected — precision loss, never used for money in this codebase)
Reason: DecimalField(14,2) is the repository's canonical money representation, used consistently across all customer-facing financial models.
Affected code: OrderOffer.price_amount field definition
Risks: None — matches existing patterns
Status: Accepted
```

## ADM-011: Existing Deadline Engine Reuse

```
Decision ID: ADM-011
Context: Need 30-minute hold mechanism. Repository has PaymentDeadline infrastructure.
Decision: Extend existing PaymentDeadline model to support OrderOffer hold target.
Alternatives considered:
  A. Extend PaymentDeadline (accepted — reuse existing scheduler, retry, audit infrastructure)
  B. Create separate deadline engine (rejected — duplicates infrastructure)
  C. Use Django-Celery-Beat directly (rejected — bypasses existing audit/retry logic)
  D. Use simple datetime check (rejected — no scheduler integration, no retry)
Reason: PaymentDeadline already has: scheduler integration, retry logic, idempotent expiry, audit logging, feature gates. Extending it avoids duplicating this infrastructure.
Affected code: PaymentDeadline model (add nullable order_offer FK), PaymentDeadlineService (add create_for_offer method)
Risks: Must not break existing commission deadline workflow — mitigated by nullable FK and separate creation path
Status: Accepted in principle — pending contract-level compatibility proof (see Remediation 2 in contract)
```

## ADM-012: PaymentIntent → OrderOffer Link (1:N)

```
Decision ID: ADM-012
Context: One OrderOffer may have multiple PaymentIntents (retries). The original contract proposed
         OrderOffer.payment_intent FK (1:1), which cannot safely represent multiple attempts.
Decision: Add nullable order_offer FK to PaymentIntent. Remove payment_intent FK from OrderOffer.
Alternatives considered:
  A. OrderOffer.payment_intent FK (rejected — 1:1 cannot represent retries)
  B. PaymentIntent.order_offer FK (accepted — 1:N, each retry is a new intent)
  C. Use metadata only (rejected — unvalidated JSON is not integrity-enforced)
Reason: Multiple retries are a real user scenario. The 1:N relationship on PaymentIntent is the
        least invasive safe design. confirm_payment() receives and validates the exact successful intent.
Affected code: PaymentIntent model (add nullable FK), OrderOffer model (remove payment_intent FK)
Risks: Migration adds nullable FK to PaymentIntent — safe, no data migration needed
Status: RESOLVED_IN_CONTRACT
```

## ADM-013: One Canonical OrderOffer per (order, supplier)

```
Decision ID: ADM-013
Context: Phase 1 initially implemented a conditional UniqueConstraint allowing multiple offers
         per (order, supplier) when older offers reached terminal status. Architecture review
         determined this creates ambiguous identity: a supplier could have ACCEPTED, EXPIRED,
         and WITHDRAWN offers on the same order simultaneously, making reporting, audit trails,
         and future service logic unreliable.
Decision: Exactly one canonical OrderOffer exists per (order, supplier). The unconditional
         UniqueConstraint enforces this at the database level. A second row must never be
         created. Future resubmission (after withdrawal, expiry, etc.) updates or reactivates
         the existing record.
Alternatives considered:
  A. Conditional uniqueness on active statuses only (rejected — ambiguous identity, unreliable audit)
  B. Unconditional uniqueness (accepted — stable identity, clean audit history, reliable reporting)
  C. Separate offer history table (rejected — over-engineered for Phase 1, can be added later)
Reason: Unconditional uniqueness provides: (1) stable identity for every supplier's relationship
        to an order, (2) complete audit history in one row, (3) reliable reporting and aggregation,
        (4) simpler service logic with no edge cases around status transitions.
Affected code: OrderOffer model Meta.constraints, migration 0008_orderoffer.py
Risks: Future "resubmit" logic must update the existing row, not create a new one. This is a
       design constraint that must be enforced in OrderOfferService.submit_offer().
Status: VERIFIED_IN_IMPLEMENTATION — unconditional constraint in place, 40 tests passing
```

## ADM-014: VerificationDocument.rejection_reason Becomes Owner-Visible

```
Decision ID: ADM-014
Context: Phase 1.1 (Manual Document Verification) implements the platform-admin review
         workflow apps.accounts.models.media's own module docstring named as future/
         out-of-scope for Epic 06 Sprint 2. That Sprint declared rejection_reason
         "Staff-authored, internal-only — never rendered on any provider/organization-facing
         or public page." The current task's explicit business requirement #6 is the direct
         opposite: "The document owner can see: current review status; rejection/correction
         reason; whether resubmission is required."
Decision: rejection_reason is now rendered on the owning caregiver's/organization's own
         portal page (document_upload.html, via document_status.html's action_message prop)
         whenever the document's status is REJECTED or CORRECTION_REQUIRED. It is still never
         rendered on any PUBLIC page (public_site caregiver/organization profiles are
         untouched by this task).
Alternatives considered:
  A. Keep rejection_reason internal-only; add a second, separate "owner-facing message" field
     (rejected — a genuine second field the reviewer would have to fill out twice, and the
     task's own governance says "do not create parallel status/data systems" without cause;
     no such duplication was needed once the internal-only constraint itself was reconsidered)
  B. Reverse the internal-only constraint, reuse the existing field for both purposes
     (accepted — the field's actual content, a reviewer's plain-language reason, was never
     unsafe to show its own subject; the Sprint 2 restriction predates this task's explicit
     opposite requirement)
Reason: A reviewer's reason for rejecting a document is written FOR the person who must act on
        it. Continuing to hide it would make "request correction" meaningless (the owner would
        not know what to correct) and directly contradicts this task's explicit spec.
Affected code: apps/accounts/models/media.py (VerificationDocument.rejection_reason docstring),
        ui/components/portal/document_status.html (action_message prop docstring),
        templates/provider_portal/document_upload.html, templates/organization_portal/document_upload.html
Risks: None — the field's content is authored by platform staff specifically to be actionable
        by the document owner; no PII/internal-system data was ever stored there by design
        (DisputeResolveForm-style internal notes live elsewhere, e.g. AuditLog.reason, and
        remain internal).
Status: RESOLVED_IN_IMPLEMENTATION — 41 tests passing (25 service + 16 view), including
        explicit owner-visibility and cross-tenant/self-review denial coverage
```

## ADM-015: Profile Verification Roll-Up Reuses the Existing 4-Value Enum; VERIFIED Documents Are No Longer Owner-Replaceable

```
Decision ID: ADM-015
Context: Phase 1.2 (Verification Completion and Activation Rules) had to derive
         CaregiverProfile/OrganizationProfile.verification_status from required-document
         state (Part B), and had to implement an owner resubmission path for
         CORRECTION_REQUIRED documents (Part C). Two design questions arose that the task's
         own governance ("Reuse the existing profile verification status. Do not create a
         second source of truth.") and explicit Part C requirement ("approved documents
         cannot be silently replaced") both had direct bearing on.

Decision 1 — no fifth enum value: VerificationStatus (UNVERIFIED/PENDING/VERIFIED/REJECTED)
         is reused exactly as-is. A required document in CORRECTION_REQUIRED maps to
         profile-level PENDING (same tier as "still awaiting first review" — both are
         "not yet resolved, action needed, not a hard block"), with a separate
         `needs_correction: bool` flag on VerificationRollupResult carrying the distinction
         instead of a new enum member.
Alternatives considered:
  A. Add VerificationStatus.CORRECTION_REQUIRED (rejected — a new field-choices migration,
     and every existing reader of this field across the codebase — presentation services
     in provider_portal/organization_portal, public_site — would need updating to handle a
     5th value it doesn't expect; the task explicitly forbade a second source of truth,
     and a 5th enum value that most readers can't distinguish from PENDING anyway isn't
     meaningfully different from just returning PENDING + a side-channel flag)
  B. Map CORRECTION_REQUIRED to profile REJECTED (rejected — overstates the severity; a
     correction request is not a hard negative decision, and folding it into REJECTED would
     make ActivationEligibilityService's "documents_not_verified" reason indistinguishable
     from an actual rejection, losing exactly the signal Part D needs to report structured
     reasons)
  C. PENDING + needs_correction flag (accepted)

Decision 2 — DocumentService.resubmit() hardens replace_document(): before this phase, any
         caregiver/organization could reset an ALREADY-VERIFIED document straight back to
         PENDING at any time via the existing upload form (replace_document() applied no
         status check). Part C's explicit "approved documents cannot be silently replaced"
         closes this. resubmit() is now the sole authorized entry point reachable from a
         request; replace_document() remains its lower-level file-swap primitive.
Alternatives considered:
  A. Leave replace_document() as the only method, add the guard there directly (rejected —
     VerificationReviewService and any other trusted internal caller would then also be
     blocked from ever resetting a VERIFIED document even in a legitimate system-initiated
     scenario; separating the raw primitive from the owner-authorized entry point keeps
     that door open without weakening the owner-facing guarantee)
  B. New resubmit() wrapping replace_document() with ownership + status checks (accepted)

Reason: Both decisions follow the same principle — extend behavior at the correct layer
        (a result field, a wrapping method) rather than widening a shared enum or weakening
        a shared primitive that other trusted callers rely on.
Affected code: apps/accounts/services/verification_rollup_service.py (new),
        apps/accounts/services/document_service.py (resubmit() added),
        apps/accounts/services/document_ownership.py (new, shared helper extracted from
        verification_review_service.py to avoid duplicating tenant/owner resolution)
Risks: None identified — 47 new tests cover both decisions directly (state-mapping matrix,
        VERIFIED-replacement refusal, concurrency for both resubmit() and sync_*()).
Status: RESOLVED_IN_IMPLEMENTATION — full regression 1768/1768 green
```

## ADM-016: Profile Activation Is an Audited Approval Record, Not a New Lifecycle State

```
Decision ID: ADM-016
Context: Phase 1.3 (Complete Phase 1 Activation and Profile Completion) required wiring
         ActivationEligibilityService (Phase 1.2, read-only) into a real, controlled
         activation action (Part B/C), while explicitly forbidding a parallel activation
         state system and requiring reuse of existing status enums. Repository inspection
         confirmed CaregiverProfile.status/OrganizationProfile.status already default to
         ProfileStatus.ACTIVE at registration (unchanged, stable, pre-existing behavior —
         grep confirmed no code path currently creates a DRAFT profile) and that
         ActivationEligibilityService's existing `status == ACTIVE` precondition is itself
         unchanged Phase 1.2 behavior this task must not weaken. This created an apparent
         circularity if "activation" were read as a DRAFT/SUSPENDED -> ACTIVE status
         transition: a profile cannot become eligible while inactive, yet activation is
         supposed to make an inactive profile active.

Decision: ProfileActivationService.activate_caregiver()/activate_organization() is the
         formal, audited, permission-gated record of platform approval — not a new
         database lifecycle state and not the thing that makes `status` become ACTIVE in
         the common case (it already is, by registration default). Concretely:
         1. It calls ActivationEligibilityService.evaluate(profile) unchanged and refuses
            with the service's own structured reasons if ineligible.
         2. If eligible, it sets `status = ProfileStatus.ACTIVE` only if not already ACTIVE
            (a no-op in the overwhelmingly common case) and writes a permanent
            `AuditLog` entry (`action="accounts.profile.activated"`).
         3. Idempotency for an already-activated profile is determined by AuditLog
            existence (tenant + resource_type + resource_id + action), not a new model
            field — the same non-field-based idempotency pattern already used elsewhere
            in this codebase (apps.commission's idempotency-key lookups), applied here as
            "has this exact approval already been recorded."
         4. SUSPENDED remains a genuine, still-blocking eligibility failure that
            activate_*() cannot override — ActivationEligibilityService's `status ==
            ACTIVE` check is untouched, so activation is explicitly NOT a path out of
            suspension in this slice (a separate suspension/revalidation workflow, if
            built later, owns that transition).
         5. A regression-proof test (`NoAutomaticDeactivationTest`, using
            `inspect.getsource()`) asserts `ProfileActivationService`'s source never
            references `ProfileStatus.SUSPENDED`/`ProfileStatus.ARCHIVED` — proving no
            deactivation logic was introduced by this change.

Alternatives considered:
  A. Add a new `PENDING_ACTIVATION` (or similar) ProfileStatus value, with registration
     creating profiles in that state instead of ACTIVE, and activate_*() transitioning
     PENDING_ACTIVATION -> ACTIVE (rejected — this is exactly the "redesign stable
     architecture" / "parallel activation state" the task's own governance forbids; it
     would require a migration, would change registration's committed, tested behavior,
     and would ripple into every existing reader of `status` including
     `is_publicly_visible()` and the Phase 1.2 eligibility check itself)
  B. Add a new boolean/timestamp field (e.g. `activated_at`) on CaregiverProfile/
     OrganizationProfile to record activation (rejected — a real, if small, migration
     for a fact the AuditLog already records durably and queryably; violates "prefer no
     migration" and duplicates the audit trail as a second source of truth)
  C. Audited approval record over the existing AuditLog, `status` transition only where
     truly not-yet-ACTIVE, activation authority owned by platform staff only (accepted)

Activation authority: `ACCOUNTS_PROFILE_ACTIVATE` (platform-scoped permission, registered
         in `apps/kernel/permissions/keys.py`, granted to `platform_owner`/`platform_admin`/
         `platform_support` in `DEFAULT_TENANT_ROLES` alongside the Phase 1.1
         `ACCOUNTS_DOCUMENT_REVIEW` grant — the two are now grouped under
         `PLATFORM_VERIFICATION_PERMISSIONS`, renamed from the Phase 1.1
         `DOCUMENT_REVIEW_PERMISSIONS` tuple, no other references existed). Owner
         self-activation is refused as defense-in-depth inside the service itself
         (actor's `UserAccount.id` compared against the profile owner's), independent of
         RBAC grants — mirrors the same pattern `VerificationReviewService` already
         established for self-review refusal (ADM-014). Cross-tenant activation is refused
         by resolving the locked profile's own tenant before permission enforcement and
         returning "not found" rather than "forbidden" (matches the existing cross-tenant
         404 convention used throughout admin_portal).

Deferred (explicitly, per task instruction): automatic deactivation of an already-active
         profile when verification later becomes invalid/expired. No suspension/
         revalidation workflow exists in this repository to hook such a deactivation into;
         inventing one was out of scope. Eligibility itself does correctly flip to
         ineligible when a required document expires (Phase 1.2's existing
         `is_effectively_expired()` behavior, unchanged) — only the *active* profile's
         `status` field is not automatically walked back. Recorded here as a known,
         intentional gap, not an oversight — see `quality/COMPLETION_BACKLOG.md` BG-019.

Reason: Reusing the existing default-ACTIVE status and the existing AuditLog as the
        approval record avoids inventing a second, parallel notion of "active" while still
        delivering a real, controlled, permission-gated, auditable activation action with
        concurrency-safe idempotency — exactly what Part B/C require without redesigning
        stable, already-tested architecture.
Affected code: apps/accounts/services/profile_activation_service.py (new),
        apps/accounts/services/profile_completion_service.py (new, Part A — see below),
        apps/kernel/permissions/keys.py, apps/accounts/permission_keys.py,
        apps/admin_portal/permission_keys.py, apps/kernel/role_catalog.py,
        apps/admin_portal/views.py + urls.py (4 new thin-controller views/routes,
        mirroring the existing document_verification_* view shape),
        apps/provider_portal/services/{viewmodels.py,profile_service.py},
        apps/organization_portal/services/{viewmodels.py,profile_service.py}
        (owner-facing activation status added alongside, not replacing, the pre-existing
        portal-specific completion widget — see Part A decision below).
Risks: None identified — 40 new tests cover eligible/ineligible/expired/unauthorized/
        cross-tenant/self-activation/repeated/concurrent activation, plus owner- and
        platform-facing UI.
Status: RESOLVED_IN_IMPLEMENTATION — full regression 1808/1808 green

---------------------------------------------------------------------------------------
REMEDIATION (PR #5 follow-up), 2026-07-15 — corrects the decision above
---------------------------------------------------------------------------------------

PR review (before merge) found a genuine defect in the ADM-016 design above: because
`CaregiverProfile.status`/`OrganizationProfile.status` already defaulted to
`ProfileStatus.ACTIVE` at registration (an unchanged, pre-existing fact this ADM leaned
on), `ProfileActivationService` never actually needed to perform a real status transition
in the common case — activation degenerated into "write an `AuditLog` entry," with
`is_activated()` reading that `AuditLog`'s existence rather than the profile's own
`status`. That made `AuditLog` — meant to be a permanent record of what happened — into
the thing that *decided* current state, which is backwards: a historical log must never
be a live source of truth, and nothing prevented that log from getting out of sync with
reality (or, as a dedicated regression test now proves, being written directly with no
real transition behind it at all).

Corrected rules (supersede the "Idempotency without a new field" section above):

1. **`profile.status` is the sole source of truth for current activation state.**
   `ProfileActivationService.is_activated(profile)` now returns
   `profile.status == ProfileStatus.ACTIVE` directly — no `AuditLog` query, no separate
   signal that could drift from the real column value.
2. **Registration now starts caregiver/organization profiles in `ProfileStatus.DRAFT`**,
   not `ACTIVE`. `RegistrationService.create_caregiver()`/`create_company_admin()` and the
   multi-role bootstrap helper `ensure_caregiver_profile()` (`apps.accounts.services
   .profiles`) now pass `status=ProfileStatus.DRAFT` explicitly at the `.objects.create()`
   call site. `DRAFT` already existed in the `ProfileStatus` enum (defined, unused for
   this purpose, since the enum was introduced) — no new status value was invented.
3. **`ActivationEligibilityService` no longer requires `status == ACTIVE` as an eligibility
   precondition** (the exact circularity this remediation targets: a DRAFT profile could
   never become "eligible" under the old rule, so it could never be activated). It now
   blocks only `SUSPENDED`/`ARCHIVED` (`BLOCKING_PROFILE_STATUSES`); `DRAFT` and `ACTIVE`
   are both non-blocking. The reason code changed from `profile_status_not_active:{status}`
   to `profile_status_blocked:{status}` to reflect the corrected semantics.
4. **`ProfileActivationService._activate()` now performs the real `DRAFT -> ACTIVE`
   transition** and returns a structured `ProfileActivationResult(profile, previous_status,
   status, transitioned)`. Idempotency is now judged by `profile.status == ACTIVE` (not
   `AuditLog` existence) — a repeated call against an already-`ACTIVE` profile returns
   `transitioned=False` without re-running eligibility (so a profile activated once stays
   activatable/idempotent even if some later fact would have made a *fresh* activation
   attempt fail — that is the same deferred deactivation/revalidation gap BG-019 already
   named, not a new one). `AuditLog.before_snapshot`/`after_snapshot` now record the real
   `{"status": "draft"}` -> `{"status": "active"}` transition.
5. **`SUSPENDED` is refused, not silently ignored**, via the same `ProfileActivationError`
   path as any other ineligibility — no special-cased exception type was needed because
   `ActivationEligibilityService` already reports `profile_status_blocked:suspended` as a
   normal blocking reason.

No model-field default change, no migration: `CaregiverProfile.status`/
`OrganizationProfile.status`'s own Django field default remains `ProfileStatus.ACTIVE`,
unchanged. Repository-wide inspection (grep across every app) found exactly three
production code paths that create a `CaregiverProfile`/`OrganizationProfile` at all —
`RegistrationService.create_caregiver()`, `RegistrationService.create_company_admin()`,
and `ensure_caregiver_profile()` — all three now pass `status=ProfileStatus.DRAFT`
explicitly. Every other creation site in the repository (test fixtures across `accounts`,
`provider_portal`, `organization_portal`, `admin_portal`, `orders`, `booking`,
`commission`; the `seed_demo_people`/`seed_demo_accounts` dev-only management commands)
creates profiles directly via `.objects.create()`, outside the canonical registration
layer, and is unaffected by this remediation — changing the model-level default instead
would have silently flipped status for all of those call sites too, a far wider blast
radius than this remediation's scope, including tests in apps this task is explicitly
forbidden from touching (Marketplace/Financial/Booking — `apps.orders.services
.eligibility_service.OrderEligibilityService.is_eligible()` and `apps.accounts.services
.supplier_bridge.is_organization_supplier_active()` both read `organization.status ==
ProfileStatus.ACTIVE` for unrelated marketplace/financial-core purposes and were not
touched). This was judged the smallest correct fix per the task's own instruction: "If
changing the model field default is necessary to prevent unsafe creation outside those
services, make the minimal migration" — no such external unsafe path exists, so no
migration is necessary.

Known, accepted, out-of-scope consequence: a caregiver/organization created through the
real registration flow is no longer counted `ACTIVE` by
`OrderEligibilityService.is_eligible()`/`is_organization_supplier_active()` until platform
staff formally activate it. This is the intended effect of making activation a real,
explicit, authorized action rather than a byproduct of registration — not a bug, and not
a change to any Marketplace/Financial/Booking code itself.

Affected code (remediation): `apps/accounts/services/registration.py`,
`apps/accounts/services/profiles.py` (`ensure_caregiver_profile()`),
`apps/accounts/services/activation_eligibility_service.py`,
`apps/accounts/services/profile_activation_service.py` (rewritten),
`apps/admin_portal/views.py`, `apps/provider_portal/services/profile_service.py`,
`apps/organization_portal/services/profile_service.py`, the two `*ViewModel`s (new
`activation_profile_status` field), `ui/components/portal/activation_status.html` and the
two `admin_portal` activation-detail templates (explicit SUSPENDED badge).
Status: RESOLVED_IN_IMPLEMENTATION (remediation) — full regression 1824/1824 green

---

Part A of the same task (deterministic profile completion) is a smaller, independent
decision recorded briefly here rather than as its own ADM: `ProfileCompletionService`
(new) becomes the single source of truth for the base-profile-field checklist per profile
type (caregiver: 7 fields; organization: 6 fields), returning `percent`/`completed`/
`missing`. `apps.accounts.services.profiles.calculate_caregiver_profile_completion()`/
`calculate_organization_profile_completion()` now delegate their percentage to it instead
of duplicating field lists, preserving their existing bare-int call signature for all
existing callers (`ActivationEligibilityService`, `apps.portal.services.profile_service`).
Deliberately NOT merged with `provider_portal`/`organization_portal`'s own pre-existing
`_completion()` methods, which compute a different, blended metric (base fields + "at
least one verified document approved") for portal-specific UI purposes predating this
task — unifying them would change owner-visible completion percentages on working,
untouched code, against "do not modify unrelated code." The new activation-status UI
fields (`is_activated`, `activation_eligible`, `activation_blocking_reasons`) were added
alongside the existing `completion_percent`/`completion_missing_labels` fields instead.
```

## ADM-017: Caregiver Professional Profile Foundation — Ownership, Public/Private Boundary, and Credential-Summary Derivation

```
Decision ID: ADM-017
Context: Phase 2.1 (Caregiver Professional Profile Foundation) required deciding (1)
         which aggregate owns new professional-profile data (skills, experience), (2)
         where the public/private eligibility boundary for the single caregiver public
         profile page lives, and (3) how a "verified credential summary" is derived
         without ever exposing VerificationDocument's private fields.

Decision 1 — canonical ownership: no second caregiver identity or parallel profile was
         created. `CaregiverSkill`/`CaregiverExperience` (new) are plain FKs to the
         existing `CaregiverProfile`, following the exact shape `VerificationDocument`
         already established for caregiver-owned child records in `apps.accounts`
         (plain `models.Model`, UUID PK, FK + `related_name`, no `TenantAwareModel`
         base — tenant is derived transitively via `caregiver.user.tenant`). No new
         "professional profile" aggregate, no gallery/social table. Public biography,
         headline, city, and avatar/cover are NOT new fields — `CaregiverProfile.bio`,
         `.specialty` (already the free-text field rendered as the public profile's
         subtitle — reused as-is as the "professional headline/title," not duplicated
         under a new name), `.city`, `.avatar`, `.cover_image` already existed and were
         already read by `apps.public_site.services.profile_service
         .CaregiverPublicProfileService` and edited by `apps.accounts.services
         .caregiver_profile_service.CaregiverProfileUpdateService`. "Services offered"
         needed no new model or service either — `ServiceSupplier.service_categories`
         (a kernel-owned JSON list of `ServiceCategory` ids) plus
         `SupplierRegistry.set_service_categories()` and
         `CaregiverProfileUpdateService.update_professional_info(service_category_ids=…)`
         already implemented full caregiver-editable services-offered management (Epic 06
         Sprint 2) — this phase only added the missing *public-facing* read path
         (`service_names`, already present in `CaregiverProfileViewModel`, confirmed
         reused not reinvented). "Languages" and "issuing organization" metadata were
         explicitly NOT added — no existing field or model supports either, and this
         phase's own governance forbids inventing a presentational field with no
         product evidence behind it.
Alternatives considered:
  A. A new `CaregiverProfessionalProfile` 1:1 table holding headline/bio/etc.
     (rejected — `CaregiverProfile` already owns every one of those fields; a second
     table would either duplicate them or split one concept across two rows for no
     reason)
  B. Reuse CaregiverProfile/CaregiverSkill/CaregiverExperience directly, no new
     aggregate (accepted)

Decision 2 — public/private eligibility boundary lives in
         `CaregiverPublicProfileService.get_profile()` only, not in the shared
         `apps.public_site.services.common.is_publicly_visible()` function the
         caregiver directory and home-page featured-caregiver listings also call.
         This phase's own governance is explicit that eligibility applies to "a
         caregiver public profile" (the single-profile page), and requires: profile
         status ACTIVE, account active, activation approval complete, verification
         roll-up VERIFIED, no suspension/archive, valid tenant/supplier relationships.
         `common.is_publicly_visible()` already covered profile-status-ACTIVE and
         organization-membership-active (existing, Architecture Review M1/M2) — since
         the Phase 1.3 remediation, `profile.status == ACTIVE` is genuinely the
         "activation approval complete" signal (never inferred from AuditLog — ADM-016),
         so that existing check already satisfied two of the six criteria correctly.
         It never checked the rolled-up `verification_status` or the owning account's
         own `is_active` — both added, but as a *local, additional* check inside
         `get_profile()` (`_is_profile_page_eligible()`), composed with (never
         replacing) the shared function.
Alternatives considered:
  A. Add `verification_status == VERIFIED` and `account.is_active` directly into the
     shared `common.is_publicly_visible_attrs()` (tried first; reverted). This is the
     single-source-of-truth-looking option, but it silently tightened the caregiver
     directory and home-page listings too — surfaces this phase never inspected or was
     asked to change — and broke ~80 pre-existing directory/home-page tests whose
     fixtures default to `verification_status="unverified"` (a lax default those
     features apparently relied on intentionally, or at least never had reason to
     tighten). Changing discovery/listing eligibility is a real product decision this
     phase has no evidence for, and "do not silently expand scope" / "do not redesign
     stable architecture" both weigh directly against it.
  B. A second, parallel eligibility function private to `apps.public_site.services
     .profile_service` (rejected — would duplicate the profile/membership-active logic
     `common.is_publicly_visible()` already implements correctly, recreating exactly the
     "two sources of truth" problem this phase's own governance repeatedly warns
     against)
  C. Keep `common.is_publicly_visible()` unchanged; add the two new checks as a local,
     composed addition inside the single-profile page's own service only (accepted) —
     narrowest correct scope, zero behavior change to directory/home-page listings,
     zero pre-existing test breakage outside the two profile-page tests whose fixtures
     genuinely needed `verification_status="verified"` added (which is the correct fix,
     not a workaround — those tests were asserting "a normal caregiver's profile page
     is visible," and a caregiver with no verification is not a realistic "normal"
     case).
Risks: Directory/home-page listings can now show a caregiver whose own profile *page*
        is hidden (unverified or inactive-account) — an inconsistency between "found in
        the directory" and "profile page loads." Recorded as a deferred, out-of-scope
        gap (see `quality/COMPLETION_BACKLOG.md`) rather than silently fixed by widening
        this phase's blast radius; closing it is a discovery/listing-surface decision
        for whoever owns that feature next.

Decision 3 — `PublicCredentialSelector.for_caregiver(caregiver)` (new, `apps.accounts
         .services.public_credential_selector`) derives the public credential summary
         from `VerificationDocument` directly, filtered to APPROVED
         (`DocumentStatus.VERIFIED`), not effectively expired
         (`RequiredDocumentPolicy.is_effectively_expired()`, Phase 1.2 — reused, not
         reimplemented), one of `CAREGIVER_APPLICABLE_DOCUMENT_TYPES` (Phase 1.2 —
         reused), and owned by the queried caregiver (queryset filter, never a
         caller-supplied ownership claim). Returns a frozen `PublicCredentialSummary`
         dataclass with exactly three fields (document_type, label, expiry_date) — no
         `file`, no document number (never modeled), no reviewer, no rejection/
         correction reason. "Issuing organization" and a distinct "public credential
         title" were not added (Decision 1's same reasoning: not modeled, not invented).
Alternatives considered:
  A. Let `apps.public_site` query `VerificationDocument` directly (rejected — that
     model's own docstring is explicit that only the verification *status* label may
     ever cross into public-facing code, and a selector encapsulates the exact set of
     safe fields in one place rather than trusting every future caller to filter
     correctly)
  B. A read-only selector living in `apps.accounts` (the model's owning app), called by
     `apps.public_site` with an already-resolved `CaregiverProfile` instance obtained
     via the existing duck-typed `resolve_supplier_entity()` bridge — never imports
     `CaregiverProfile`/`OrganizationProfile` by name in `apps.public_site`, so
     `apps.kernel.tests.test_architecture_guardrails
     .ServiceSupplierProfileCouplingTest` remains satisfied (accepted)
Risks: None identified — 24 accounts-level tests plus 11 public_site-level tests cover
        approved/pending/rejected/correction-required/expired exclusion, ownership
        isolation, and the absence of file/reviewer/rejection-reason fields directly.
Affected code: apps/accounts/models/professional_profile.py (new),
        apps/accounts/services/caregiver_professional_profile_service.py (new),
        apps/accounts/services/public_credential_selector.py (new),
        apps/public_site/services/profile_service.py (get_profile() local eligibility
        + skills/experience/credentials assembly), apps/public_site/services/
        viewmodels.py, apps/provider_portal/services/{profile_service.py,viewmodels.py},
        apps/provider_portal/{views.py,forms.py,urls.py}, templates under
        templates/provider_portal/ and templates/public_site/caregiver_profile.html.
Status: RESOLVED_IN_IMPLEMENTATION — 50 new tests, full regression 1874/1874 green,
        zero new migration drift beyond the two new models.

---------------------------------------------------------------------------------------
REMEDIATION (PR #6 review), 2026-07-15 — closes BG-022, corrects Decision 2 above
---------------------------------------------------------------------------------------

PR #6 review correctly identified that Decision 2's chosen alternative (C — add the two
new checks locally to `CaregiverPublicProfileService.get_profile()` only) left a real,
user-visible gap: a caregiver could be discoverable in the public directory or the
home page's featured-caregiver cards while their own detail page 404'd, because
`common.is_publicly_visible_attrs()` (the function the directory/home-page listings
already shared) never required `verification_status == VERIFIED` or account `is_active`
— only the detail page's local, duplicated check did. This was recorded at the time as
BG-022, a deliberate, scoped deferral — governance for this remediation explicitly
required closing it inside this same PR rather than leaving it deferred.

Corrected decision: **Alternative A from Decision 2 above (originally rejected) is now
adopted** — the two checks were moved into `common.is_publicly_visible_attrs()` itself,
making it the single, genuinely canonical rule for every public entry point (directory,
home-page listings, and the detail page, which now relies on it exclusively — its own
local duplicate check was deleted). The reason Alternative A was originally rejected
(breaking ~80 pre-existing directory/home-page tests whose fixtures default to
`verification_status="unverified"`) turned out to be a fixable, one-line fixture default
change (`apps/public_site/tests/helpers.py`), not the broad blast radius originally
feared — those ~80 tests never asserted anything about verification status (confirmed
by grep before changing the default) and all continued passing unmodified.

Root correction: "do not silently expand scope" was correctly applied to Decision 2's
original choice (this phase's own explicit deliverable was the detail page, not a
directory/listing overhaul), but the resulting inconsistency between two supposedly
"canonical" functions was itself a defect, not a scope boundary — a caregiver's public
visibility must have exactly one true answer everywhere it is asked. This remediation
resolves that: `common.is_publicly_visible_attrs()` is now that one true answer.

A genuine, pre-existing, unrelated per-candidate query cost (one `availability_capacity_rule`
query and one `reviews_reputation_snapshot`/`orders_order` pair per card, in
`DiscoveryRankingService.rank()`/`CaregiverDirectoryService._build_card()`) was discovered
while verifying this remediation added no new N+1. It predates this remediation and is
unrelated to eligibility — recorded as `quality/DEFECT_AND_RISK_REGISTER.md` KL-012, not
fixed here (touching `apps.discovery`'s ranking algorithm is a separate, out-of-scope
performance task).

Affected code (remediation): `apps/public_site/services/common.py` (canonical rule
extended), `apps/public_site/services/profile_service.py` (local duplicate check
removed), `apps/accounts/services/supplier_bridge.py` (`select_related("user")`/
`select_related("admin_user")` added to `resolve_supplier_entities_bulk()`, a JOIN not
an extra query), `apps/public_site/tests/helpers.py` (fixture default corrected),
`apps/public_site/tests/test_public_visibility_policy.py` (new, 13 tests).
Status: RESOLVED_IN_IMPLEMENTATION (remediation) — BG-022 closed, 13 new tests, full
        regression 1887/1887 green, zero new migration.
```
