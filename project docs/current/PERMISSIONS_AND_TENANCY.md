# PERMISSION AND TENANT MODEL

**Last verified HEAD:** phase2-caregiver-professional-profile-foundation (from main @ 0c9d70c, PR #5 merged; PR #6 BG-022 remediation in progress)
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
