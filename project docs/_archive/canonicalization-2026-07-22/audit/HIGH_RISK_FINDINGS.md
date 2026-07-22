# HIGH RISK FINDINGS

---

## FR-003: ownership_authorized_by Bypass in PermissionService

**Severity:** HIGH
**Confidence:** HIGH

**Affected subsystem:** booking, execution, commission services

**Evidence:**
- `apps/kernel/services/permission_service.py:157-188` — if `ownership_authorized_by` is set and actor has no RoleAssignment, authorization is granted
- PermissionService does NOT verify ownership — trusts the caller
- Used by: AssignmentService.assign(), ExecutionService methods

**Runtime impact:** Any service that passes `ownership_authorized_by` can bypass RBAC. Security depends on caller correctness.

**Suggested future action:** Document the trust boundary clearly. Consider adding ownership verification to PermissionService.

---

## FR-004: FakeProviderCallbackView Unauthenticated

**Severity:** HIGH
**Confidence:** HIGH

**Affected subsystem:** payments

**Evidence:**
- `apps/api/views/payments.py:72-117` — no authentication decorator
- Queries `PaymentAttempt.objects.get(provider_reference=provider_reference)` without tenant scoping
- Protected only by unguessable `provider_reference` token

**Runtime impact:** Anyone with a valid provider_reference can trigger payment state transitions.

**Suggested future action:** Add signature verification when real PSP is implemented.

---

## FR-005: Pre-Existing Seed Test Race Condition

**Severity:** HIGH
**Confidence:** HIGH (proven by baseline verification)

**Affected subsystem:** kernel/tests/test_seed_product_walkthrough.py

**Evidence:**
- Baseline verification: test passes 10/10 in isolation, fails 1/10 in full regression
- `_generate_order_number()` uses random 4-digit suffix that collides under concurrent execution
- Error: `IntegrityError: duplicate key value violates unique constraint "orders_order_order_number_key"`

**Runtime impact:** Full regression suite always has exit code 1. 1671/1672 pass.

**Suggested future action:** Fix `_generate_order_number()` to use UUID or database sequence.

---

## FR-006: UserAccount Queries Not Tenant-Scoped

**Severity:** MEDIUM
**Confidence:** HIGH

**Affected subsystem:** accounts

**Evidence:**
- `apps/accounts/views.py:86,124,163,241` — `UserAccount.objects.filter(phone=phone)` without tenant filter
- Login returns first matching account globally

**Runtime impact:** Phone numbers are globally unique login identifiers. A phone registered in tenant A is detected during tenant B's registration.

**Suggested future action:** Document this as intentional design. Consider tenant-scoped login for multi-tenant deployment.
