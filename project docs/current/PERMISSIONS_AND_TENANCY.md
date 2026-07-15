# PERMISSION AND TENANT MODEL

**Last verified HEAD:** phase2-caregiver-professional-dashboard (from main @ 125dd3b, PR #9 merged)
**Last verified date:** 2026-07-15

---

## RBAC Architecture

### Permission Key Registry

All permission keys are defined in `apps/kernel/permissions/registry.py` with regex-validated format: `{module}.{resource}.{action}`.

### Permission Enforcement

`PermissionService.require()` in `apps/kernel/services/permission_service.py`:

1. If `RBACConfiguration.get_enforcement_enabled(tenant_id)` is False → **ALL RBAC BYPASSED** (configurable per-tenant)
2. If `actor is None` and `ownership_authorized_by is None` → system context, authorized
3. Normal RBAC check via `RoleAssignment` records
4. Ownership fallback: if `ownership_authorized_by` is set and has no RoleAssignment → authorized (caller-verified)

### Role Definitions

14 role categories defined via `seed_auth_roles` management command:
- platform-owner, platform-admin, platform-support
- organization-owner, organization-admin, organization-member
- customer, family-member
- independent-provider, organization-provider
- operator, dispatcher, reviewer, auditor

### Permission Enforcement Points

| Enforcement Point | Location |
|-------------------|----------|
| Customer Portal | `portal/views.py:_guard()` → `require_authenticated()` |
| Provider Portal | `provider_portal/views.py:_guard()` → `require_authenticated()` |
| Organization Portal | `organization_portal/views.py:_guard()` → `require_authenticated()` |
| Admin Portal | `admin_portal/views.py:require_admin_permission()` |
| API | `api/permissions.py:require_permission()` |
| Services | `PermissionService.require()` called explicitly |

### Document Review Permission (Phase 1.1)

`accounts.document.review` (platform-scoped) guards `VerificationReviewService.approve()/reject()/request_correction()` and the 4 admin_portal document-verification views. Granted to `platform_owner`, `platform_admin`, `platform_support` in `apps/kernel/role_catalog.py:DEFAULT_TENANT_ROLES` — the same additive per-role-tuple pattern as `ORGANIZATION_PROFILE_UPDATE`. Note: `platform_owner`/`platform_admin`/`platform_support` in the real ("salmandyar") tenant previously carried **no permissions at all** in `DEFAULT_TENANT_ROLES` (only the separate `DEV_BOOTSTRAP_ROLES` catalog, used by `seed_tenant` for a dev-bootstrap tenant, granted `ADMIN_PORTAL_ACCESS` to a differently-slugged "platform-owner" role) — this is the first permission grant added to the real-tenant platform roles since Epic 05's `platform_accounting` addition.

Self-review is refused as defense-in-depth inside `VerificationReviewService` itself (reviewer's `UserAccount.id` compared against the document owner's), independent of whatever RBAC grants exist — mirrors the FR-003 "ownership_authorized_by trusts the caller" finding by not repeating that pattern here (this is a normal RBAC actor check, no ownership fallback).

### Profile Activation Permission (Phase 1.3)

`accounts.profile.activate` (platform-scoped, `ACCOUNTS_PROFILE_ACTIVATE`) guards
`ProfileActivationService.activate_caregiver()/activate_organization()` and the 4
admin_portal activation views. Granted to `platform_owner`, `platform_admin`,
`platform_support` in `apps/kernel/role_catalog.py:DEFAULT_TENANT_ROLES` — the tuple
carrying both this and the Phase 1.1 `accounts.document.review` grant was renamed
`DOCUMENT_REVIEW_PERMISSIONS` → `PLATFORM_VERIFICATION_PERMISSIONS` (no other references
existed, verified by grep before renaming). Owner self-activation is refused as
defense-in-depth inside `ProfileActivationService` itself (actor's `UserAccount.id`
compared against the profile owner's — `caregiver.user_id`/`organization.admin_user_id`),
independent of whatever RBAC grants exist, mirroring the same pattern
`VerificationReviewService` established for self-review refusal. Cross-tenant activation
is refused by resolving and tenant-checking the locked profile *before* permission
enforcement and returning "not found" (mirrors the existing cross-tenant 404 convention
elsewhere in `admin_portal`) rather than "forbidden". Authorization/tenancy behavior is
unchanged by the PR #5 remediation — only *what a successful activation does* (a real
`profile.status` transition, not an `AuditLog`-only record) was corrected. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-016 (including its remediation note) for
the full activation-authority design decision.

### Owner Resubmission Authorization (Phase 1.2)

`DocumentService.resubmit(document, *, actor, file)` — no new permission key (resubmission is an ownership check, not an RBAC-gated action, matching `get_owned_document()`'s existing shape). Refuses unless `actor.id` equals the document's owner user (`caregiver.user_id`/`organization.admin_user_id`, resolved via the shared `apps.accounts.services.document_ownership` helpers also used by `VerificationReviewService`) — cross-tenant and cross-owner resubmission attempts get the same `AccountsError`, and a platform reviewer cannot resubmit on an owner's behalf. Refuses to touch an already-`VERIFIED` document regardless of who calls it. Row-locked (`select_for_update()`) so concurrent resubmission attempts on the same document serialize rather than racing.

### Caregiver Skill/Experience Authorization (Phase 2.1)

`CaregiverSkillService`/`CaregiverExperienceService` — no new permission key, same ownership shape as `CaregiverProfileUpdateService`/`DocumentService.resubmit()`. The provider-portal views resolve the caller's own `CaregiverProfile` via `request.user.caregiver_profile` (`_guard_with_caregiver()`) — a customer or organization-only user has no such attribute and gets `PermissionDenied` (403) before any service call. Every service mutation additionally filters by `caregiver=caregiver` (the caller's own resolved profile, never a request-supplied id trusted as ownership proof), so a caregiver cannot edit/delete another caregiver's skill or experience row even by guessing its UUID — verified directly (not just structurally) by `test_another_caregiver_cannot_remove_skill`/`test_cannot_update_another_caregivers_experience`/`test_cross_tenant_cannot_edit_experience`, all asserting a 404/no-op rather than trusting the structural argument alone.

### Public Caregiver Profile Eligibility (Phase 2.1)

`CaregiverPublicProfileService.get_profile()` (`apps.public_site`) — read-only, unauthenticated-safe. Beyond the existing `common.is_publicly_visible()` check (profile status ACTIVE + organization-membership-active), this phase added a local, additional requirement: `verification_status == "verified"` and the owning account's `user.is_active`. Deliberately added only here, not in the shared `common.py` function the caregiver directory and home-page featured-caregiver listings also call — see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017 Decision 2 for the full reasoning and the resulting, explicitly recorded gap (those two listing surfaces do not yet apply the same stricter rule).

**BG-022 remediation (2026-07-15, same PR #6):** the gap above is closed — `is_publicly_visible_attrs()` in `common.py` is now the canonical rule and every public surface (detail page, directory, home-page listings) enforces it identically. This is not an RBAC change: public visibility remains an unauthenticated, account/profile-status-derived rule (`profile.status`, `verification_status`, account `is_active`, organization-membership `is_active`), never a permission key, and is unrelated to the `PermissionService`/`RoleAssignment` mechanism described above. See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-017's second remediation note.

### Caregiver Gallery Authorization (Sprint 2.2)

`CaregiverGalleryService` — no new permission key, same ownership shape as
`CaregiverSkillService`/`CaregiverExperienceService`/`ProfileMediaService`. The
provider-portal views resolve the caller's own `CaregiverProfile` via
`request.user.caregiver_profile` (`_guard_with_caregiver()`) — a customer or
organization-only user gets `PermissionDenied` (403) before any service call. Every
mutation additionally filters/locks by `caregiver=caregiver` (the caller's own resolved
profile, never a request-supplied id trusted as ownership proof), so a caregiver cannot
edit/reorder/remove another caregiver's gallery item even by guessing its UUID — verified
directly (not just structurally) by `test_another_caregiver_cannot_edit`/
`test_another_caregiver_cannot_remove`/
`test_another_caregiver_cannot_reorder_items_they_do_not_own`/`test_cross_tenant_cannot_edit`,
all asserting a 404/no-op rather than trusting the structural argument alone.

**Remediation (PR #7 review, 2026-07-15):** the same authorization boundary now also
governs *when physical file deletion is even scheduled* — `remove_item()` only reaches its
`transaction.on_commit()` scheduling line after the `caregiver=caregiver`-filtered row lock
has already succeeded, so an unauthorized or cross-tenant removal attempt (which raises
before that point) schedules no file deletion at all, proven directly by
`test_another_caregiver_cannot_remove` (asserts the mocked deletion callback is never
called) and `test_cross_tenant_removal_schedules_no_deletion`. Public
gallery visibility is not an RBAC concern at all — it flows entirely through the existing
BG-022 canonical `common.is_publicly_visible()` policy (profile/account/membership status),
the same as skills/experience/credentials.

### Skill/Experience Visibility Authorization (Sprint 2.3)

`CaregiverSkillService.toggle_visibility()` and `CaregiverExperienceService.create()`/
`update()`'s new `is_visible` parameter reuse the exact same ownership boundary these two
services already established in Phase 2.1 — no new permission key, no new authorization
code path. `toggle_visibility()` filters by `id=skill_id, caregiver=caregiver` in the same
`.get()` call that resolves the row (the filter itself is the authorization boundary,
identical to `remove_skill()`'s existing pattern) — verified directly by
`test_cannot_toggle_another_caregivers_skill_visibility`,
`test_another_caregiver_cannot_toggle_skill_visibility`,
`test_cross_tenant_cannot_toggle_skill_visibility`, and
`test_unrelated_organization_user_cannot_mutate_skills` (an account with no
`caregiver_profile` at all, representing an unrelated organization user — `_guard_with_
caregiver()` denies it 403 before any service call, exactly as it already does for
customers). Public precise badges and highlights are not an RBAC concern either — both are
pure, read-only derivations computed only after the existing BG-022 canonical visibility
gate has already passed.

### Caregiver Availability Authorization (Sprint 2.4)

`apps.availability` predates this sprint and already established its own ownership
convention, distinct from (but equally sound as) the `apps.accounts` filter-in-service
pattern above: `AvailabilityQueryService.get_working_window_for_supplier()`/
`get_blocked_period_for_supplier()` resolve a row scoped by `supplier=` at the call site;
only a row that resolves is ever passed on to a mutation method. `apps.provider_portal`'s
views call `_guard(request)` first (`resolve_supplier(request)` — the caller's own
`ServiceSupplier`, never accepted from the request) and then this ownership-scoped lookup
before every mutation, including the two new Sprint 2.4 views
(`working_window_update_view`, `working_window_toggle_view`) — a caregiver cannot mutate a
window/blocked-period they do not own even by guessing its UUID. Verified directly by
`test_another_provider_cannot_update_working_window`,
`test_cross_tenant_cannot_update_working_window`,
`test_another_provider_cannot_toggle_working_window`, and (pre-existing, unchanged)
`test_cannot_remove_another_providers_window`/`test_cannot_remove_another_providers_blocked_period`.
A customer or unrelated-organization-only account (no `caregiver_profile`) gets `PermissionDenied`
(403) from `_guard()` before any service call is reached — `test_customer_cannot_access_availability_page`,
`test_customer_cannot_toggle_working_window`, `test_customer_cannot_add_blocked_period`,
`test_unrelated_organization_user_cannot_mutate_availability` — the same pattern Sprint 2.3
established for skills. `AvailabilityQueryService.evaluate()` and the public schedule
summary are not RBAC concerns: `evaluate()` is a pure, read-only, supplier-keyed function
callable by any caller that already holds a `ServiceSupplier` instance, and the public
summary is gated by the existing BG-022 canonical visibility policy, exactly like
highlights/badges/gallery.

### Critical Finding: No Middleware Enforcement

There is no Django middleware that automatically:
- Injects tenant_id into queries
- Enforces authentication
- Enforces RBAC

Every view and service must independently call auth/tenant/permission checks.

## Tenant Isolation

### How It Works

1. `TenantAwareModel.save()` validates `tenant_id` is non-empty
2. `TenantScopedManager.for_tenant(tenant_id)` provides convenience filtering
3. Services accept `tenant_id` parameter and use it in queries
4. Views resolve tenant from authenticated user's session

### Critical Finding: No Automated Tenant Isolation

Tenant filtering depends entirely on every developer passing `tenant_id` to every query. A single forgotten parameter creates a cross-tenant data leak.

### Caregiver Dashboard Authorization (Sprint 2.5)

`dashboard_view` now uses `_guard_with_caregiver(request)` (already-established, unchanged
helper — `resolve_supplier(request)` + `request.user.caregiver_profile`, never accepted
from the request) to resolve the caller's own `supplier`/`tenant_id`/`caregiver` before
calling `CaregiverDashboardPresentationService.build_for_supplier()`. No new permission key,
no new authorization mechanism: every new selector this sprint added
(`OrderQueryService.list_for_supplier()`/`count_by_status_for_supplier()`,
`FinancialDocumentService.list_for_beneficiary_party()`/`count_by_status_for_beneficiary_party()`,
`ReputationService.list_recent_reviews_with_reviewer_names()`) is filtered by the caller's
own `supplier`/`party_id`/`tenant_id`, resolved exactly once at the top of the view, never
accepted as a request parameter. A customer or unrelated-organization-only account (no
`caregiver_profile`) gets `PermissionDenied` (403) from `_guard_with_caregiver()` before any
service call is reached — the same pattern every other provider-portal view already uses.
Verified directly (not just structurally) by `test_customer_cannot_access_dashboard`,
`test_unrelated_organization_user_cannot_access_dashboard`,
`test_each_provider_sees_only_their_own_dashboard`, and
`test_cross_tenant_provider_sees_only_their_own_tenant` in
`apps.provider_portal.tests.test_professional_dashboard`.

### Unscoped Queries (Known)

| Location | Query | Risk |
|----------|-------|------|
| `commission/services/authorization.py:156-159` | `FinancialParty.objects.filter(id=party_id)` | Low (UUID random) |
| `accounts/views.py:86,124,163,241` | `UserAccount.objects.filter(phone=phone)` | By design (global login) |
| `kernel/services/supplier_registry.py:69-74` | `ServiceSupplier.objects.filter(linked_entity_id=...)` | Low (UUID random) |
| `api/views/payments.py:90` | `PaymentAttempt.objects.get(provider_reference=...)` | Low (unguessable token) |

## Security Configuration

Production settings include:
- HSTS (1 year), XSS filter, content-type nosniff
- Secure cookies (session + CSRF)
- SSL redirect
- X-Frame-Options: DENY
- No `csrf_exempt` decorators found
- No `eval()`, `exec()`, `pickle.loads()` found
- No raw SQL except `SELECT 1` health check
- No `mark_safe()` with user input
