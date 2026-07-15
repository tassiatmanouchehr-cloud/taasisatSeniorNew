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

---

## ADM-018: Caregiver Gallery — Ownership, Storage, Deletion, and Limit (Sprint 2.2)

**Date:** 2026-07-15
**Status:** DECIDED
**Context:** Sprint 2.2 (Caregiver Professional Profile: Gallery and Media Portfolio) —
first PR after PR #6 (Phase 2.1 foundation) merged to `main`. Roadmap Phase 2 requires a
caregiver-managed, Instagram-like professional photo portfolio, distinct from the existing
single-field avatar/cover images and from `VerificationDocument`'s private evidence store.

**Decision 1 — Model shape and ownership.** `CaregiverGalleryItem`
(`apps/accounts/models/gallery.py`) is a new, plain `models.Model` (no `TenantAwareModel`
base), UUID PK, single FK to `CaregiverProfile` with `related_name="gallery_items"` —
copied directly from `CaregiverSkill`/`CaregiverExperience`'s established shape (Phase 2.1,
ADM-017), not from `VerificationDocument`'s dual-owner (`caregiver`/`organization`) shape,
because a gallery item only ever has one possible owner type. Tenant is derived
transitively via `caregiver.user.tenant`, never duplicated onto the child row — the same
reasoning ADM-017 already recorded for skills/experience. Rejected alternative: a generic,
polymorphic `Media`/`Attachment` model reusable across apps — no such model exists anywhere
in this repository (confirmed by repo-wide search before implementing), and
`VerificationDocument`'s own docstring already rejected the polymorphic
`linked_entity_id`/`linked_entity_type` pattern for the weaker case of two possible owners
in the same app; a gallery item's single owner type makes a dedicated model the simpler,
DB-validated choice here too.

**Decision 2 — Storage strategy.** Gallery images are stored under `public/gallery/
caregiver/<uuid4>.<ext>` (`caregiver_gallery_path()`, `media_paths.py`), the same `public/`
convention `avatar`/`cover_image`/organization `logo`/`cover_image` already use — never
`private/` (that prefix is reserved for `VerificationDocument`, the only model
`config/urls.py`'s dev `static()` helper deliberately does not serve). A gallery photo is,
by definition, meant to be shown on the public profile, so it belongs on the public side of
that existing, load-bearing split from day one — there is no "pending private review"
state for a gallery photo the way there is for a verification document.

**Decision 3 — Validation reuse, not duplication.** The Pillow-based, content-sniffing
image validator (`ProfileMediaService`'s former `_validate_image()`) was extracted verbatim
into `apps.accounts.services.image_validation.validate_image()` and both
`ProfileMediaService` and the new `CaregiverGalleryService` now call the one shared
function — behavior unchanged, MAX_IMAGE_BYTES/ALLOWED_IMAGE_FORMATS unchanged. This is the
"reuse existing validators, do not duplicate" governance rule applied literally: gallery
upload validation is not a second implementation of the same check.

**Decision 4 — Deletion is hard delete; `is_visible` is the only soft lever.** No
`is_deleted`/`archived_at`/`ArchivableModel` field exists on `CaregiverGalleryItem`.
Investigated first: `apps.common.models.SoftDeleteMixin`/`ActiveManager` exist but are used
by zero models in `apps.accounts` (confirmed by repo search) — `VerificationDocument`,
`CaregiverSkill`, and `CaregiverExperience` all hard-delete, and `ProfileMediaService
._replace()` already deletes the physical file on avatar/cover replacement/removal. Rather
than introduce a new soft-delete concept for this one model (against this app's own
established convention), gallery deletion follows the same hard-delete-plus-physical-file-
removal pattern, and `is_visible` (identical shape to `CaregiverSkill.is_visible`/
`CaregiverExperience.is_visible`) is the sole visibility lever a caregiver has short of
permanent deletion — hiding an item never deletes its file, only removes it from
`CaregiverGalleryService`'s (owner-facing) and the public selector's (`_gallery()` in
`apps.public_site.services.profile_service`) results.

**Decision 5 — Gallery limit is an explicit constant, not tenant-configurable.**
`MAX_GALLERY_ITEMS_PER_CAREGIVER = 12` (`caregiver_gallery_service.py`) is a fixed,
hardcoded cap, matching `CaregiverSkillService.MAX_SKILL_NAME_LENGTH`'s own explicit-
constant style — no product requirement or existing repo convention (e.g.
`RequiredDocumentPolicy`'s `ConfigResolver`, Phase 1.2) calls for a caregiver photo count
cap to vary per tenant. Enforced by row-locking the owning `CaregiverProfile`
(`select_for_update()`) for the duration of the count-check-then-create — the cap has no
unique-constraint equivalent to fall back on the way `uq_caregiver_skill_name` gives
`add_skill()`'s lighter, lock-free pattern, so `CaregiverGalleryService.add_item()`/
`reorder()` instead mirror `DocumentService.resubmit()`'s heavier, explicit-lock precedent.

**Decision 6 — No second public-visibility rule.** `CaregiverGalleryService`'s public
counterpart (`CaregiverPublicProfileService._gallery()`) performs no eligibility check of
its own — it only ever runs after `get_profile()`'s existing canonical
`common.is_publicly_visible(supplier)` gate (BG-022, ADM-017's second remediation note) has
already passed, and then filters to `is_visible=True` items, the identical per-item pattern
`_skills()`/`_experience()` already established. A caregiver who fails the canonical policy
never has their gallery resolved at all — not merely filtered out after the fact.

**Consequences:** One new model, one new migration (one new table with a composite index,
no altered tables). No new soft-delete concept introduced. No new
tenant-configuration mechanism introduced. No second image-validation implementation. No
second public-visibility rule. Deferred (out of this sprint's scope, per its own
governance): video support (no canonical video infrastructure exists in this repository to
reuse), AI/automatic content moderation, thumbnail/derivative-image generation (the
existing avatar/cover convention has none either — `ProfileMediaService`'s own docstring
states "no derivative image sizes" as a deliberate simplicity choice, extended here).

---

## ADM-018 Remediation — File-Lifecycle Transaction Safety and Decoded-Image Limits (PR #7 review, 2026-07-15)

PR #7 review found two bounded gaps in the design above, neither invalidating any of the
six decisions recorded — both closed in place, on the same branch/PR, without touching
Sprint 2.2's model, storage strategy, or public-visibility composition.

**Gap 1 — file-deletion transaction order.** `CaregiverGalleryService.remove_item()`
originally deleted the physical file (`image.delete(save=False)`) *before* deleting the
database row, inside the same `transaction.atomic()` block. Filesystem operations do not
participate in a database transaction — if anything after the file deletion caused that
transaction (or an outer transaction this call was nested inside) to roll back, the row
would be restored while the file it points to was already gone: a live row referencing a
dead file. **Fixed:** the row is deleted first; the storage handle and stored file name are
captured beforehand (since `item.image` is unusable once the row is gone); physical
deletion is scheduled via `transaction.on_commit()`, which Django guarantees to run only
after the outermost enclosing transaction actually commits — and to discard entirely,
never run, if that transaction instead rolls back. The database is therefore never left
inconsistent by this operation in either outcome. No model signal was used for this — the
scheduling happens directly in the same service method that performs the deletion, matching
this codebase's "every mutation goes through an explicit service call, not an implicit
signal" convention.

**Gap 2 — storage-deletion failure behavior (defined, not left implicit).** If the
post-commit physical deletion itself fails (a storage/filesystem error), the failure is
caught and logged (`logger.exception(...)`), never re-raised: by the time it runs, the row
is already durably gone (committed) and cannot be un-deleted by this failure, and the
item's public URL is already unreachable (nothing resolves the deleted row anymore) — the
only possible consequence is an orphaned file left on disk, now detectable via the log.
Retrying or sweeping orphaned files is explicitly **deferred** — no cleanup-job
infrastructure exists anywhere in this repository to hook automatic retry into, and
building one was out of this narrowly-scoped remediation's mandate ("do not implement a
broad background-cleanup subsystem").

**Gap 3 — decoded-image safety limits.** `image_validation.validate_image()` bounded the
*compressed* upload size (`MAX_IMAGE_BYTES`) but not the *decoded* image dimensions — a
small, adversarially-crafted file can declare an enormous pixel grid
("decompression bomb"), and the byte-size cap alone does nothing to stop it. **Fixed:**
`MAX_IMAGE_WIDTH`/`MAX_IMAGE_HEIGHT`/`MAX_IMAGE_PIXELS` (8000px / 8000px / 25M px,
explicit constants, not tenant-configurable — matching every other numeric limit in this
module's own style) are read from the image header immediately after `Image.open()` — a
cheap, non-decoding read — and enforced before any full pixel decode is ever attempted.
Pillow's own `Image.DecompressionBombError` (raised outright for extreme cases) and
`DecompressionBombWarning` (only warned by default; promoted to a catchable exception here
via a scoped `warnings.simplefilter("error", ...)`) are both caught as defense-in-depth and
mapped to the same controlled `AccountsError` — never a raw exception, never a 500.
Validation remains a single decode pass (open once, read format/size, `verify()` once) —
no re-opening, no repeated decoding of the same bytes. The file stream is reset to
position 0 after validation, exactly as before, so the subsequent `ImageField` save still
reads the file from the start.

Affected code: `apps/accounts/services/caregiver_gallery_service.py` (`remove_item()`
restructured; new `_delete_stored_file()`), `apps/accounts/services/image_validation.py`
(`MAX_IMAGE_WIDTH`/`MAX_IMAGE_HEIGHT`/`MAX_IMAGE_PIXELS` added; decompression-bomb handling
added). No model or migration change — these are service-layer behavior corrections only.
16 new tests, full regression 1948/1948 green.
Status: RESOLVED_IN_IMPLEMENTATION (remediation).

---

## ADM-019: Precise Verification Badges, Derived Highlights, and Self-Declared vs. Verified Distinction (Sprint 2.3)

**Date:** 2026-07-15
**Status:** DECIDED
**Context:** Sprint 2.3 (Credentials, Skills, Experience, Highlights) — first sprint on a
fresh branch after PR #7 (Sprint 2.2 gallery + remediation) merged to `main`. Completes the
professional-credibility presentation layer: precise verification badges, an owner-
completable visibility toggle for skills/experience (the `is_visible` column has existed on
both models since Phase 2.1, unused until now), a minimal derived highlights summary, and
an owner-facing "expiring soon" credential state.

**Decision 1 — No new public credential metadata field.** `PublicCredentialSelector`/
`PublicCredentialSummary` already carry exactly `document_type`, `label`, `expiry_date` —
the full set of safe metadata `VerificationDocument` actually models. "Issuing
organization" and a distinct "issue date" were explicitly considered (per this sprint's own
governance: "only if explicitly public and modeled") and rejected — neither field exists on
`VerificationDocument`, and inventing either would be presenting a fact the platform never
actually captured. `PublicCredentialViewModel` gained one new field,`document_type` (a type
code like `"identity"`, not evidence), so the presentation layer can derive precise
per-type badges without a new query or a new model field.

**Decision 2 — Precise badges, never one generic "Verified."** The public profile
previously showed a single `"تأییدشده"` (Verified) pill tied to the coarse
`verification_status` flag — a compound claim conflating "this profile passed the
canonical visibility gate" with "this specific credential is authentic." Replaced with
`VerificationBadgeViewModel` entries, each naming exactly one claim: "نمایه تأییدشده"
(Profile verified — the profile passed the canonical BG-022 gate), "هویت تأییدشده"
(Identity verified — an approved, unexpired IDENTITY document exists), "مدرک حرفه‌ای
تأییدشده" (Professional credential verified — at least one approved credential of any
type exists). Under the *default* required-document policy, "Profile verified" and
"Identity verified" always co-occur (IDENTITY is mandatory) — but the badges remain
independently correct, evidence-derived facts, not aliases of each other, and a tenant that
narrows its required-document policy (`RequiredDocumentPolicy`, already tenant-overridable
since Phase 1.2) can genuinely decouple them; a test in
`apps.public_site.tests.test_professional_profile_public
.PublicProfileHighlightsAndBadgesTest.test_badges_never_imply_broader_approval_than_evidence`
proves this using exactly that override mechanism.

**Decision 3 — Highlights are derived, never a new stored statistic.** `years_experience`
is an existing `CaregiverProfile` attribute; `verified_credential_count` is `len()` of the
already-resolved credentials tuple; `visible_skill_count` is `len()` of the already-
resolved skills tuple; `completed_jobs_count`/`review_count` are values `get_profile()`
already computed for the rating sidebar. Nothing here is written to a new column, and
nothing here issues a new query on the public page (confirmed unchanged at 14 queries by
the existing `PublicProfileQueryCountTest`). The provider-portal owner-side highlights
preview (`HighlightsViewModel`) mirrors the same shape but necessarily issues two new,
fixed-cost `.count()` queries of its own (`visible_skill_count`/`visible_experience_count`
require a `WHERE is_visible` filter distinct from the pre-existing unfiltered
`skills_count`/`experience_count`) — the provider profile page's own locked query-count
baseline moved 13 -> 15 accordingly, proven fixed-cost (not per-item) by the unchanged test
structure.

**Decision 4 — Self-declared experience is never presented as platform-verified.** No
experience-verification record exists anywhere in this repository, and this sprint's own
governance explicitly forbids implying one. A plain-text disclaimer
("این سوابق توسط خود مراقب اعلام شده و توسط پلتفرم تأیید نشده است.") was added directly to
the public experience section — a template-level clarification, not a new derived field,
since there is nothing to derive: the absence of verification is the fact being stated. The
adjacent credentials section gained a matching, contrasting disclaimer confirming *those*
values *are* platform-reviewed — making the distinction legible by direct contrast, not by
inference.

**Decision 5 — Skill model stays free-text; no catalog migration.** `CaregiverSkill.name`
remains a free-text `CharField` (Phase 2.1's original decision, ADM-017) — this sprint's own
governance explicitly warned against "silently redesigning" it. The ambiguity a skill
catalog would resolve (e.g. spelling variants of the same skill never merging in search/
filter contexts) is real but out of scope; recorded as a deferred, future catalog-migration
risk (`quality/DEFECT_AND_RISK_REGISTER.md` KL-016), not addressed here.

**Decision 6 — `is_expiring_soon()` is owner-facing only, never public.** A 30-day window
constant (`RequiredDocumentPolicy.EXPIRING_SOON_WINDOW_DAYS`), mirroring
`is_effectively_expired()`'s existing shape (derived, point-in-time, no DB mutation). The
public `PublicCredentialSelector` was not touched at all for this — a still-valid,
still-approved credential is shown publicly exactly as before regardless of how soon it
expires; "expiring soon" is purely an owner-facing action prompt
(`verification_badge.html`'s new `expiring_soon` status branch, reached only from
`ProviderProfilePresentationService._document_rows()`).

**Consequences:** Zero new models, zero new migrations (both `is_visible` columns already
existed; every other change is either a new field on an existing dataclass or a purely
derived value). One shared UI component (`verification_badge.html`, also used by
`organization_portal`) gained one new, purely additive status branch — verified not to
affect any existing status rendering, and `apps.organization_portal`'s own test suite
(51/51) re-run to confirm. 36 new tests, full regression 1984/1984 green.

---

## ADM-020: Caregiver Availability and Working Schedule (Sprint 2.4)

Decision ID: ADM-020
Date: 2026-07-15
Status: RESOLVED_IN_IMPLEMENTATION

**Context:** Sprint 2.4's governance asked for a caregiver-facing weekly schedule, time-off
management, one canonical read-only availability evaluator, a public availability summary,
and a provider-portal preview of that summary — explicitly warning "do not create a
duplicate scheduling source of truth." Current-state inspection found `apps.availability`
(Module 10 foundation, predating this sprint) already owns the entire domain:
`ProviderWorkingWindow` (weekly recurring intervals), `AvailabilityBlockedPeriod` (time-off/
exceptions), `AvailabilityQueryService`/`AvailabilityMutationService`, and a working
`apps.provider_portal` add/remove UI — all keyed on `kernel.ServiceSupplier`, never
`CaregiverProfile`. This sprint's task was substantially completion, not creation.

**Decision 1 — The canonical evaluator stays supplier-keyed; no new caregiver-keyed
service.** The governance's suggested shape was
`CaregiverAvailabilityService.evaluate(caregiver, start_at, end_at)`. That shape is not
adopted literally: `apps.availability` sits below `apps.accounts` in this repository's own
dependency graph (`kernel -> accounts -> orders -> ... -> availability`), and its own module
docstring already commits to never importing `CaregiverProfile`/`OrganizationProfile`
directly (mirroring the same `ServiceSupplierProfileCouplingTest` guardrail
`apps.public_site`/`apps.provider_portal` already respect). A caregiver-shaped entry point
living *inside* `apps.availability` would invert that dependency; one living in
`apps.accounts` would create a new upstream->downstream edge in the wrong direction, since
`apps.accounts` must not import `apps.availability`. Instead, `AvailabilityQueryService
.evaluate(*, supplier, start, end) -> AvailabilityEvaluation` is the one canonical,
structured evaluator (`is_supplier_available()` is now a thin bool-only wrapper around it —
zero behavior change, all 20 pre-existing tests pass unmodified). `apps.provider_portal` and
`apps.public_site` — both already resolving their own `ServiceSupplier` before needing an
evaluation — call it directly. No caregiver-keyed duplicate was created.

**Decision 2 — The evaluator never inspects booking/execution state.** Section E's item 6
("existing confirmed bookings or execution sessions, only if a canonical conflict selector
already exists and can be reused without expanding scope") was evaluated and declined:
`apps.booking.services.assignment_service` already calls
`AvailabilityQueryService.is_supplier_available()` as one input among several before
confirming an assignment — booking is a *consumer* of this evaluator, not a peer selector to
merge into it. Folding booking-conflict awareness into the evaluator itself would invert that
relationship and risk circular coupling (`apps.availability` sits below `apps.booking`).
Recorded as explicitly out of scope, not a gap.

**Decision 3 — Weekly intervals refuse overlap/duplicates; blocked periods do not.**
`AvailabilityMutationService.add_working_window()`/`update_working_window()` now refuse a
duplicate or overlapping *active* window on the same day for the same supplier (Section C).
Blocked periods deliberately keep their pre-existing, already-tested behavior of allowing
overlaps — `apps.availability.tests.test_query_service.AvailabilityQueryServiceTest
.test_overlapping_blocked_periods_both_apply` already proved this is harmless, established
repository behavior (redundant unavailability, not a conflict) before this sprint began;
adding refusal here would be an undocumented behavior change to a passing, intentional test,
not a bug fix.

**Decision 4 — Public schedule presentation is summarized, never exact.** The public profile
shows only which weekdays have at least one active working window
(`AvailabilityScheduleSummaryViewModel.available_day_labels`, Persian day names) — never
start/end times, and never anything about `AvailabilityBlockedPeriod` (reason, notes, or even
existence). This satisfies Section F's "expose a summarized form" guidance directly: exact
hours are a scheduling-coordination detail, not a public marketing fact, and blocked-period
data is explicitly private (leave reason, sick notes) with no public use case. Proven by
`apps.public_site.tests.test_professional_profile_public.PublicScheduleSummaryTest
.test_summary_never_exposes_exact_times`/`test_summary_never_exposes_blocked_period_details`.

**Decision 5 — Time zone stays platform-wide; no per-caregiver field.** No per-tenant or
per-caregiver time-zone field exists anywhere in this repository (confirmed by inspection).
`AvailabilityQueryService` already resolved all times via Django's default
`timezone.localtime()`/`settings.TIME_ZONE` (`Asia/Tehran`) before this sprint;
`evaluate()`'s new `timezone` field reports `timezone.get_current_timezone_name()` — the same
single, deterministic source, now surfaced in the structured result rather than left
implicit. Per Section J's explicit fallback instruction, this is documented as a known
limitation, not fixed: every caregiver on the platform is scheduled in the same platform
time zone regardless of their own physical location. A genuine per-caregiver time zone would
require a new `CaregiverProfile` field and is deferred (`quality/COMPLETION_BACKLOG.md`
BG-024), not invented here without evidence of demand.

**Decision 6 — Ownership stays view-layer resolve-then-mutate; no service-layer signature
change.** `apps.availability`'s pre-existing convention (already proven secure by
`test_cannot_remove_another_providers_window`) resolves a row via
`get_working_window_for_supplier()`/`get_blocked_period_for_supplier()` at the call site,
then mutates by verified id — not a `supplier=` filter parameter inside the mutation methods
themselves (the pattern `apps.accounts`'s Sprint 2.1/2.3 services use instead). This sprint's
new `working_window_update_view`/`working_window_toggle_view` reuse the exact same
existing pattern rather than introducing a second, parallel ownership mechanism inside one
app.

**Consequences:** Zero new models, zero new migrations — both `ProviderWorkingWindow` and
`AvailabilityBlockedPeriod` already existed with every field this sprint needed.
`apps.public_site` gains one new, documented cross-app edge to `apps.availability` (a valid
direction: both sit at the terminal-UI layer alongside `apps.provider_portal`, which already
had this edge). One shared translation table, `apps.availability.models.PERSIAN_DAY_LABELS`,
added next to `DayOfWeek` so both consuming apps share one label source instead of two. Public
profile query count moved 14 -> 15 (one new fixed-cost query,
`get_distinct_active_days()`), proven O(1) by the pre-existing gallery-item-count scaling
test. Provider-portal availability page query count newly locked at 9 (no prior baseline
existed). Full regression run once before PR creation.

---------------------------------------------------------------------------------------
REMEDIATION (PR #9 review), 2026-07-15 — proves and enforces the concurrency invariant
Decision 3 above assumed but never verified
---------------------------------------------------------------------------------------

**Deferred at initial implementation:** the original Sprint 2.4 report explicitly listed
"multi-threaded concurrency race testing for the overlap-validation `select_for_update()`
path" as deferred, "consistent with this repository's existing testing conventions" — but
inspection during this remediation found there was no `select_for_update()` on the relevant
path to begin with for the case that mattered most. This was a genuine gap, not a merely
untested-but-safe design.

**Review finding — the root race:** `_validate_no_overlap()` is a plain, unlocked `SELECT`.
`add_working_window()` took no lock at all before its check-then-insert — under PostgreSQL's
default READ COMMITTED isolation, two concurrent transactions creating overlapping windows
for the same supplier/day could both read "no conflict" before either committed, then both
insert (`transaction.atomic` guarantees each transaction is all-or-nothing, not that
concurrent transactions serialize their reads against each other). `update_working_window()`
already called `select_for_update()`, but only on the window row being updated — this did not
close the gap: a concurrent `add_working_window()` touches no existing window row at all, and
two concurrent `update_working_window()` calls against two *different* windows of the same
supplier/day each lock a different row, so neither blocks the other's overlap check. This is
exactly the "lock only the candidate row" anti-pattern the review governance named.

**Fix — canonical lock boundary:** both `add_working_window()` and `update_working_window()`
now lock the owning `kernel.ServiceSupplier` row (`select_for_update()`) as the *first*
statement inside their `transaction.atomic` block, before any overlap check or window-row
lock. This mirrors `apps.accounts.services.caregiver_gallery_service
.CaregiverGalleryService.add_item()`'s existing, pre-dating precedent for the identical shape
of problem — a cross-row invariant ("no two active windows overlap this day," "count < N")
with no single-row database constraint to enforce it, resolved by locking the stable parent
row rather than a not-yet-existing or individually-scoped child row. `update_working_window()`
resolves the target window's `supplier_id` with a plain (unlocked) read first — a window's
supplier never changes after creation, so this is safe — then locks the supplier before
locking the window row itself, in the same supplier-then-window order `add_working_window()`
uses; the two methods therefore never deadlock against each other by acquiring locks in
reverse order. `toggle_working_window()` needed no change — it already delegates to
`update_working_window()` and inherits the fix.

**Alternative considered and rejected:** a PostgreSQL `ExclusionConstraint` (GiST index,
`&&` range-overlap operator) would enforce the same invariant at the database level,
independent of application code. Rejected for this remediation because it requires a new
migration, and the review governance's own preferred solution was explicit
application-level locking mirroring an existing repository pattern — "if the repository
already has an equally strong database constraint, prove it instead of adding duplicate
locking" implies locking is the default when no such constraint already exists, which
inspection confirmed (no exclusion/check constraint existed on `ProviderWorkingWindow`
before or after this remediation).

**Toggle-enable safety confirmed:** enabling a disabled window now runs through the exact
same locked, validated path as creating or updating an active window — no separate code
path exists for "enable." Disabling a window remains unconditional (no overlap check
applies to a disabled window, matching the established "disabled intervals do not count as
available" rule) and idempotent (disabling an already-disabled window is a safe no-op,
proven by a dedicated test). Two disabled, mutually-conflicting windows may still coexist
(pre-existing, established policy, ADM-020 Decision 3 above) — only the *transition* to
active is guarded.

**Concurrency test evidence:** 9 new tests in `apps.availability.tests.test_concurrency`
(`TransactionTestCase`, real separately-committed transactions on separate threads/
connections, mirroring `apps.booking.tests.test_concurrency`'s established pattern exactly)
proving: concurrent overlapping creates yield exactly one success; concurrent exact-duplicate
creates yield exactly one success; a concurrent create-vs-update pair whose *outcomes* would
conflict (though their *inputs* individually did not) yields exactly one success and leaves
zero pairwise overlaps in the final database state; concurrent enabling of two
mutually-conflicting disabled windows yields exactly one enabled window; enabling a disabled
window that overlaps an already-active window is refused; a non-overlapping mutation remains
possible immediately after the first transaction commits; a caller can immediately retry
after a refused mutation in the same process; two different suppliers never block each other
and remain tenant-isolated under concurrent load; disabling a window is idempotent. Every
test asserts final database state (not merely the raised/absent exception).

**Performance impact:** One additional `SELECT ... FOR UPDATE` per mutation (the supplier
row), held only for the duration of that single transaction. Contention is scoped to
concurrent availability mutations against the *same* supplier — proven independent across
different suppliers by `ConcurrentDifferentSuppliersTest`. No other code path in this
repository locks `ServiceSupplier` via `select_for_update()` (confirmed by grep), so this
introduces no new contention with bookings, assignments, or any other supplier-touching
operation.

**Consequences:** Zero new models, zero new migrations — `_validate_no_overlap()` and every
existing test's expected behavior are unchanged; only the locking boundary around it changed.
Files changed: `apps/availability/services/mutation_service.py` (locking added),
`apps/availability/tests/test_concurrency.py` (new, 9 tests). `apps.availability` (65/65) and
`apps.provider_portal` (107/107) full suites green; full regression run once (production
locking/mutation code changed), 2033/2033 green (2024 baseline + 9 new). Booking suite not
re-run — `AvailabilityQueryService`/`is_supplier_available()` (booking's own dependency) were
not touched by this remediation.

---

## ADM-021: Caregiver Professional Dashboard — Read-Model Architecture and Financial Source Selection (Sprint 2.5)

Decision ID: ADM-021
Date: 2026-07-15
Status: RESOLVED_IN_IMPLEMENTATION

**Context:** Sprint 2.5 asked for a caregiver-facing dashboard summarizing current/upcoming/
completed/cancelled work, a financial overview, wallet movements, bonus/penalty, invoices,
reviews/reputation, and professional statistics — all read-only, all sourced from canonical
selectors, none newly invented. Current-state inspection found `apps.provider_portal
.views.dashboard_view` already existed with a partial version of this (pending assignments,
active visits, `ProviderReportService` performance stats, reputation, notifications) — this
sprint completes it rather than replacing it.

**Decision 1 — One canonical, additive read-model ViewModel, not a wrapper around the whole
page.** `CaregiverDashboardViewModel` (assembled by the new
`apps.provider_portal.services.dashboard_service.CaregiverDashboardPresentationService`)
carries only this sprint's five new sections (`work_summary`, `financial_overview`,
`invoice_summary`, `reputation`, `statistics`) as a single `dashboard` context variable.
It deliberately does **not** re-wrap `dashboard_view`'s pre-existing, already-tested context
keys (`pending_assignments`, `active_visits`, `completed_visits`, `recent_notifications`) —
doing so would have risked silently changing already-passing behavior for no benefit. The
shape mirrors `apps.portal.services.dashboard_service
.CustomerDashboardPresentationService` (the customer-side equivalent) exactly: a `build()`
classmethod that performs no query of its own, fed by a `build_for_supplier()` classmethod
that does the actual data-gathering — kept in the service layer, not
`provider_portal/views.py`, so that file stays entirely free of direct model/ORM access
(its own module docstring's "no ORM access of any kind" rule, which the automated
`ProviderPortalOrmDisciplineTest` guardrail only partially enforces — it matches `.objects.`
calls, not related-manager calls like `caregiver.skills.filter(...)`, so this decision holds
even where the guardrail itself would not have caught a violation).

**Decision 2 — Work summary keys off `Order.status`, not `SupplierAssignment`/
`ExecutionSession` state.** Two new methods were added to the existing, canonical
`apps.orders.services.queries.OrderQueryService` (never a new query service):
`list_for_supplier()` (mirrors `list_for_customer()`'s exact shape) and
`count_by_status_for_supplier()` (one aggregate query). `Order.status` was chosen as the
single source of truth for "current/upcoming/completed/cancelled" because it is the same
field `apps.portal`'s customer dashboard already uses for the identical grouping (parity
across both portals), and because it is what `apps.execution.services.session_service`
itself transitions via `apps.orders.services.status_machine.start_order()`/
`complete_order()` — not a second, independently-derived status. No new status values were
invented; the four groupings map directly onto `OrderStatus.IN_PROGRESS`/`WAITING_SERVICE`/
`COMPLETED`/`CANCELLED`.

**Decision 3 — Professional statistics deliberately reuse two different, already-canonical
"completed" definitions without forcing them to agree.** `ProfessionalStatisticsViewModel
.completed_jobs` reuses `apps.reporting.services.provider_report_service
.ProviderReportService.get_report_for_supplier()` (CLOSED `ExecutionSession` count — a
pre-existing, Module 16 definition, unchanged) rather than the new Order-status-based
`WorkSummaryViewModel.completed_count`. Both are legitimate, independently-canonical counts
of two related-but-distinct things (an Order reaching status COMPLETED vs. an
ExecutionSession reaching status CLOSED); forcing them to share one number would have meant
silently redefining one of the two pre-existing, tested contracts. Documented explicitly per
field (see `ProfessionalStatisticsViewModel`'s own field-level docstrings) rather than left
ambiguous.

**Decision 4 — Bonus/penalty: no canonical representation exists, so none was built.**
Confirmed by inspection (grep across the entire repository) that no dedicated bonus/penalty
model, field, or `WalletTransactionType` value exists — `apps.wallet.models
.WalletTransactionType` has CREDIT/DEBIT/REFUND/PROMOTION/ADJUSTMENT/MANUAL, none carrying a
bonus/penalty semantic, and the only other repository-wide hits for "bonus"/"penalty" are an
unrelated matching/discovery ranking-score concept and a comment referencing a
never-built, reserved-for-a-future-PR cancellation-penalty engine. Per this sprint's own
explicit governance ("if no canonical representation exists, do not invent one"), no
bonus/penalty section was built. `FinancialOverviewViewModel.bonus_penalty_note` documents
this gap directly in the UI rather than presenting an invented CREDIT/DEBIT-based
classification as fact — the existing, unfiltered recent-wallet-movements list already shows
every CREDIT/DEBIT/ADJUSTMENT regardless of category.

**Decision 5 — Invoice summary reuses `FinancialDocument`'s existing `beneficiary_party`
side via a new, mirrored selector.** `apps.finance.services.document_service
.FinancialDocumentService` already had `list_for_payer_party()` (the customer/payer side,
used by `apps.portal`'s own payments page) but no equivalent for the beneficiary side (who a
document pays out to — a caregiver's own `FinancialParty`, resolved the same way
`apps.provider_portal.views.earnings_view` already resolves it for the wallet). Added
`list_for_beneficiary_party()` and `count_by_status_for_beneficiary_party()`, mirroring the
payer-side method's exact shape — not a new financial calculation, the identical
`FinancialDocument` rows every other invoice view already reads, filtered by the other of
its two existing party columns.

**Decision 6 — Recent reviews resolved inside `apps.reviews`, not queried directly from
`apps.provider_portal`.** `apps.public_site.services.profile_service
.CaregiverPublicProfileService._reviews()` already queries `Review`/`Person` directly (both
are unrestricted by `ServiceSupplierProfileCouplingTest`, unlike `CaregiverProfile`/
`OrganizationProfile`) — but `apps.provider_portal/views.py` holds itself to a stricter,
self-declared "no ORM access of any kind" standard than the automated guardrail technically
enforces (see Decision 1). `ReputationService.list_recent_reviews_with_reviewer_names()` was
added to keep that promise literal, not just guardrail-compliant.

**Consequences:** Zero new models, zero new migrations — every new method is a read-only
extension of an already-existing, canonical query service
(`OrderQueryService`/`FinancialDocumentService`/`ReputationService`), never a new query
service or a new business calculation. `apps.provider_portal/views.py` gains zero new direct
model/ORM references. Dashboard query count newly locked at 31 (empty) / 30 (populated with
1 order + up to 20 wallet transactions, proven not to grow with row count) — no prior
baseline existed for this expanded page. 44 new tests across `apps.orders` (8),
`apps.finance` (6), `apps.reviews` (6), and `apps.provider_portal` (24). Full regression run
once (multiple domain apps touched), 2077/2077 green (2033 baseline + 44 new).

## ADM-022: Public Profile Finalization and Phase 2 Acceptance — Scope Boundary Decisions (Sprint 2.6)

**Context:** Sprint 2.6 is explicitly an integration/quality/privacy/accessibility/
performance closeout sprint for the caregiver public-profile slice, not a new-capability
sprint — its governance repeatedly forbids redesigning domain engines, inventing new public
APIs, or making caching a prerequisite. Several judgment calls below have lasting
consequences for how future sprints should treat this surface, so they are recorded here
rather than left implicit in a diff.

**Decision 1 — Removed the redundant generic verification badge from the public profile
header, kept only the precise Sprint 2.3 badges.** `templates/public_site/caregiver_profile
.html` rendered two separate verification indicators: `profile.verification_badges` (Sprint
2.3's precise per-evidence badges — "نمایه تأییدشده" / "هویت تأییدشده" / "مدرک حرفه‌ای
تأییدشده") in the header, and a second, generic `profile.verification_label`/`is_verified`
badge lower on the page. Because `common.is_publicly_visible_attrs()` (BG-022) already
requires `verification_status == "verified"` for the page to render at all, that second
badge was **not situationally variable** — it always rendered "تأییدشده" (verified) with an
"info" variant on every single caregiver whose profile could ever be viewed publicly. It
conveyed zero information beyond what the header's "نمایه تأییدشده" badge already states,
in different words, immediately above it. Removed as a genuine contradictory/redundant-claim
defect under this sprint's own explicit Section B requirement ("no contradictory badge or
claim semantics") — not a redesign of the verification-badge system itself (`_verification_
badges()` in `apps/public_site/services/profile_service.py` is untouched). `ReviewViewModel
.reviewer_name`, `CaregiverCardViewModel.verification_label`/`is_verified`, and
`ProviderProfileViewModel.verification_status`/`is_verified` are unrelated fields (a
different ViewModel, or a legitimately-informative directory-card checkmark, or the owner's
own dashboard) and were deliberately left untouched.

**Decision 2 — No caching introduced.** The repository has a real, production-configured
cache (`django.core.cache.backends.redis.RedisCache`, falling back to `LocMemCache` when
`REDIS_URL` is unset — `config/settings/base.py`), but its only existing usage
(`ConfigResolver`, `FeatureFlagService`) is narrow, explicit-key, explicit-`cache.delete()`
config/feature-flag caching — never a per-request read-model or page cache. Section G's own
query-count measurement (below) found every caregiver-profile-related page's query count
either already bounded and non-growing (empty/populated public profile: 15; provider
dashboard: 30-31; provider profile-management: 15) or growing with total matching-candidate
count in a way that is a pre-existing, already-documented, out-of-scope ranking-engine
limitation (KL-012), not something a page-level cache would appropriately paper over without
its own invalidation design. No proven performance blocker exists that would justify
introducing a new caching layer/pattern in a sprint explicitly scoped to avoid broad
infrastructure work. Documented as a deferred, later operational concern, not attempted.

**Decision 3 — No new public API created.** `/api/v1/discovery/suppliers/`
(`apps.api.views.discovery.SupplierDiscoveryListView`) already exists but is permission-gated
(`DISCOVERY_SUPPLIERS_READ`) and calls `apps.discovery.services.DiscoveryService.search()`
directly — a different, internal/permission-scoped search surface than the public,
canonical-visibility-gated caregiver profile (`CaregiverPublicProfileService`). No product
requirement in this sprint's governance calls for a new, unauthenticated public read API for
caregiver profiles; the existing public HTML surfaces (directory, home, detail page) already
serve that need. Recorded as reviewed-and-deferred, not built, per the sprint's explicit "do
not create a broad new API surface merely because the sprint mentions APIs" instruction.

**Decision 4 — `DiscoveryRankingService.rank()`'s per-candidate query cost (KL-012) was
measured and quantified this sprint, not fixed.** New query-count tests
(`apps.public_site.tests.test_phase2_acceptance.Phase2QueryBudgetAcceptanceTest`) confirm the
directory page's query count grows with total matching candidates before pagination (measured:
28 queries at 5 candidates, 43 at 10, 57 at 20) and the home page's featured-caregivers
section similarly grows despite its fixed `limit=4` output (measured: 27, 32, 42 queries at
the same candidate counts), because `CaregiverDirectoryService.search()`/`.featured()` both
call `DiscoveryRankingService.rank()` on the full candidate queryset before slicing. Fixing
this requires changing `apps.discovery`'s shared ranking engine (used beyond the caregiver
directory) — explicitly out of scope for a sprint whose own governance says "do not redesign
domain engines" and "do not add ranking changes unless required to fix a proven defect." The
existing eligibility/visibility resolution itself remains genuinely O(1) regardless of
candidate count (BG-022's own `bulk_supplier_attrs()`, unaffected) — only the ranking/card-
enrichment layer scales with candidate count. Left as a recorded, quantified, out-of-scope
performance risk (KL-012, cross-referenced from this ADM entry), not a Phase 2 blocker.

**Decision 5 — One pre-existing, environment-clock-dependent test bug fixed
(`apps.accounts.tests.test_caregiver_professional_profile
.PublicCredentialSelectorExpiryTest.test_expired_document_does_not_appear`), unrelated to
this sprint's own scope.** The test computed "yesterday" via `datetime.date.today()` (OS-local
naive clock) while the code under test (`RequiredDocumentPolicy.is_effectively_expired()`)
compares against `timezone.now().date()` (Django's UTC-based clock) — the two disagree
whenever the OS-local calendar day has already advanced past UTC's, which this sprint's own
full-regression run happened to hit. Fixed by using the same `timezone.now().date()`
reference the test is actually exercising — a one-line, test-only correctness fix, not a
change to `apps.accounts`' verification-expiry logic itself. Included here because Phase 2
acceptance requires "full tests are green," and this genuinely blocked that claim on the run
that surfaced it.

**Consequences:** Zero new models, zero new migrations. Five template files touched
(accessibility/SEO/redundant-badge fixes only — no new views, no new selectors, no new
routes). One new cross-app acceptance test file
(`apps/public_site/tests/test_phase2_acceptance.py`, 5 tests) plus one one-line test fix.
2082/2082 full regression green (2077 baseline + 5 new). See
`quality/DEFECT_AND_RISK_REGISTER.md` KL-012 and KL-021, `quality/COMPLETION_BACKLOG.md`
BG-027, and `project docs/PHASE_2_COMPLETION_REPORT.md`.

## ADM-022 Remediation — Resolve the KL-012 Query-Performance Blocker (PR #11 review, 2026-07-15)

**Context:** PR #11 review found Decision 4 above internally inconsistent: it reported
directory/home query counts that visibly grew with candidate count (28/43/57 and 27/32/42)
in the same PR that declared Phase 2 acceptance criterion #17 ("query behavior is bounded")
and #21 ("no unresolved Phase 2 blocker remains") satisfied. Per this repository's own
Phase 2 acceptance bar, a query cost that scales with total matching-candidate count before
pagination is not "bounded" merely because it was measured and documented — it had to be
fixed unless proven not candidate-count-dependent, and it was proven to be exactly that.

**Root cause — three independent per-candidate query sources, not one:**

1. `DiscoveryRankingService._score()` called `CapacityService.is_capacity_exceeded(supplier=
   supplier)` once per candidate inside `rank()`'s scoring loop — one (or two, if the
   supplier has an active `CapacityRule`) query per candidate, for every candidate passed to
   `rank()`, before any pagination/limit slicing.
2. `SupplierSearchService.filter_suppliers()` — only when a `city` filter was applied —
   called `resolve_supplier_entity(supplier)` (the *singular* accounts-bridge resolver, not
   the already-existing `resolve_supplier_entities_bulk()`) once per candidate inside a
   Python list comprehension, for every candidate matching the base queryset before city
   filtering.
3. `CaregiverDirectoryService._build_card()` called `common.rating_summary(supplier)` and
   `common.completed_jobs_count(...)` once per *built* card — bounded by `PAGE_SIZE`/`limit`,
   not by total candidate count, but still one query pair per card rather than one query pair
   per page.

Sources 1 and 2 caused the unbounded (candidate-count-scaling) growth Decision 4 measured.
Source 3 caused the smaller, page-size-bounded growth visible between 1 and `PAGE_SIZE`
candidates.

**Fix — batched at the canonical selector boundary, ranking/filtering semantics unchanged:**

- `CapacityService.bulk_is_capacity_exceeded(supplier_ids)` (new, `apps.availability`) —
  2 queries total regardless of candidate count (one `CapacityRule` lookup, one grouped
  `SupplierAssignment` count). `DiscoveryRankingService.rank()` now computes this map once
  and passes it through `_score()`/`_capacity_bonus()`; the single-supplier
  `is_capacity_exceeded()` is unchanged and still used by `provider_portal`/
  `organization_portal`'s own single-caregiver capacity display.
- `SupplierSearchService._filter_by_city()` (new, replacing the inline per-candidate
  `_matches_city()`) — calls the pre-existing `resolve_supplier_entities_bulk()` (built for
  exactly this class of problem during Epic 06's Architecture Review remediation M1) instead
  of the singular resolver.
- `CaregiverDirectoryService._build_card()` now takes a precomputed `card_data` map, built
  once per `search()`/`featured()` call by a new `_bulk_card_data()` — backed by two new bulk
  methods, `ReputationService.get_reputation_summaries_bulk()` (`apps.reviews`) and
  `common.completed_jobs_counts_bulk()` (`apps.public_site`), each one aggregate query
  regardless of how many cards are being built.

No ranking weight, scoring formula, sort order, tie-break rule, pagination behavior, filter
semantics, or public-visibility policy changed — proven by the full pre-existing
`apps.discovery`/`apps.availability`/`apps.public_site` suites passing unchanged (763 tests
across the touched apps, plus the complete 151-test `apps.public_site` suite), and by a new
explicit ranking-order test
(`Phase2QueryBudgetAcceptanceTest.test_ranking_order_unchanged_by_the_query_optimization`).

**Result:** Directory, filtered search (text + city), and home-featured query counts are now
fully flat (not merely bounded-with-a-ceiling) from 1 to 100+ matching candidates — measured
16 (directory), 17 (filtered search), 17 (home featured) at every candidate count from 1
through 100 in the same measurement pass. KL-012 is RESOLVED, not merely documented. 12 new
tests (`Phase2QueryBudgetAcceptanceTest`, expanded from 3 to 15 methods) prove the invariant
directly: no growth 1→5, no material growth 5→20, a stable maximum from 20→100, for
directory, text search, category filter, city filter, and home-featured independently, plus
pagination correctness, hidden/ineligible exclusion, rating/service-category correctness,
ranking-order preservation, no added private card fields, and unchanged detail-page
behavior. Full regression 2094/2094 green (2082 baseline + 12 new). See
`quality/DEFECT_AND_RISK_REGISTER.md` KL-012 (now marked RESOLVED) and
`project docs/PHASE_2_COMPLETION_REPORT.md`.
