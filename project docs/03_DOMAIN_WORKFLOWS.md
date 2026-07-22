# DOMAIN WORKFLOWS

Every workflow in this document is reconstructed directly from repository source code. Every transition references the actual function that performs it.

---

## 1. Registration

**Purpose:** Create user accounts with role-appropriate profiles.

**Actors:** Customer, Caregiver, Company Admin

**Preconditions:** Valid Iranian phone number

**State Machine:** None (one-shot creation)

**Execution Steps:**

1. User enters phone number → `accounts/views.py:register_*_view`
2. OTP challenge created → `accounts/services/otp.py`
3. User verifies OTP → `accounts/views.py:verify_otp_view`
4. Account created:
   - Customer: `RegistrationService.create_customer()` → CustomerProfile (status=ACTIVE)
   - Caregiver: `RegistrationService.create_caregiver()` → CaregiverProfile (status=DRAFT)
   - Company: `RegistrationService.create_company_admin()` → OrganizationProfile (status=DRAFT)

**Models:** Person, UserAccount, CustomerProfile/CaregiverProfile/OrganizationProfile, OTPChallenge

**Services:** `accounts/services/registration.py`, `accounts/services/otp.py`

**Permissions:** None (public registration flow)

**Audit Events:** Account creation logged

**Transaction:** Single atomic block per registration

**Failure:** Invalid phone → form error. OTP mismatch → retry. Duplicate phone → error.

**Tests:** `accounts/tests/test_registration.py`

---

## 2. Identity Verification

**Purpose:** Platform staff review uploaded identity/professional documents to verify caregivers and organizations.

**Actors:** Document owner (caregiver/organization), Platform reviewer (staff)

**Preconditions:** Profile exists (DRAFT or ACTIVE), document uploaded

**State Machine:**

```
Document:  PENDING → VERIFIED | REJECTED | CORRECTION_REQUIRED
Profile:   UNVERIFIED → PENDING → VERIFIED | REJECTED
```

**Execution Steps:**

1. Owner uploads document → `DocumentService.upload_caregiver_document()` / `upload_organization_document()`
2. Platform staff reviews → `VerificationReviewService.approve()` / `.reject()` / `.request_correction()`
3. Rollup auto-evaluates → `ProfileVerificationRollupService.sync_caregiver()` / `.sync_organization()`
4. If all required docs VERIFIED + unexpired → profile `verification_status = VERIFIED`
5. Owner may resubmit rejected docs → `DocumentService.resubmit()`

**Models:** VerificationDocument, CaregiverProfile.verification_status, OrganizationProfile.verification_status

**Services:** `accounts/services/verification_review_service.py`, `accounts/services/verification_rollup_service.py`, `accounts/services/document_service.py`, `accounts/services/verification_policy.py`

**Permissions:** `accounts.document.review` (platform staff only)

**Audit Events:** `accounts.document.reviewed`, `accounts.document.resubmitted`

**Transaction:** Atomic per review action; rollup runs in same transaction

**Tests:** `accounts/tests/test_verification_review.py`, `accounts/tests/test_verification_rollup.py`, `accounts/tests/test_document_resubmission.py`

---

## 3. Profile Activation

**Purpose:** Authorized transition of a profile from DRAFT to ACTIVE, creating the marketplace ServiceSupplier record.

**Actors:** Platform staff

**Preconditions:** Profile verification_status = VERIFIED, profile_completion = 100%, user is_active, profile not SUSPENDED/ARCHIVED

**State Machine:**

```
Profile:  DRAFT → ACTIVE (via ProfileActivationService)
```

**Execution Steps:**

1. Staff navigates to activation page → `admin_portal/views.py:caregiver_activation_detail` / `organization_activation_detail`
2. Staff confirms activation → `ProfileActivationService.activate_caregiver()` / `.activate_organization()`
3. Service checks eligibility → `ActivationEligibilityService.evaluate()`
4. If eligible: `profile.status = ACTIVE` + `supplier_bridge.sync_supplier_for_profile_activation()`
5. ServiceSupplier record created/synced via `SupplierRegistry.get_or_create_supplier()`
6. AuditLog entry written

**Models:** CaregiverProfile/OrganizationProfile, ServiceSupplier

**Services:** `accounts/services/profile_activation_service.py`, `accounts/services/activation_eligibility_service.py`, `accounts/services/supplier_bridge.py`, `kernel/services/supplier_registry.py`

**Permissions:** `accounts.profile.activate` (platform staff only)

**Audit Events:** Profile activation with before/after status

**Transaction:** Single atomic block; ServiceSupplier sync included

**Tests:** `accounts/tests/test_profile_activation.py`, `accounts/tests/test_profile_supplier_invariant.py`

---

## 4. Marketplace (Public Visibility)

**Purpose:** Determine which suppliers appear on public directories and profile pages.

**Actors:** Anonymous visitors, authenticated customers (for favorites)

**Preconditions:** None for viewing

**Visibility Rule** (single canonical function: `public_site/services/common.py:is_publicly_visible_attrs()`):

ALL of:
- `profile_status == "active"`
- `verification_status == "verified"`
- owning account `is_active == True`
- `supplier.status == "active"`
- For organization-affiliated caregivers: membership is active

**Tenant Resolution** (`public_site/services/tenant_context.py:resolve_public_tenant()`):
1. Explicit `?tenant=<slug>` query parameter
2. `settings.PUBLIC_SITE_TENANT_SLUG` (if configured)
3. DEBUG-only: `CANONICAL_DEV_TENANT_SLUG` auto-resolution
4. Platform default tenant

**Services:** `public_site/services/directory_service.py` (caregiver), `public_site/services/organization_directory_service.py`, `public_site/services/profile_service.py`, `public_site/services/home_service.py`

**Tests:** `public_site/tests/test_public_visibility_policy.py`, `public_site/tests/test_canonical_tenant_resolution.py`

---

## 5. Order Workflow

**Purpose:** Customer requests a service; the order progresses through approval, assignment, execution, and completion.

**Actors:** Customer, Platform operator, Assigned supplier

**State Machine:**

```
PENDING_OPERATOR_REVIEW → NEW → WAITING_SERVICE → IN_PROGRESS → COMPLETED
                                                                    ↑
                        (any non-terminal) → CANCELLATION_REQUESTED → CANCELLED
```

**Execution Steps:**

| Step | Function | From | To |
|---|---|---|---|
| Customer submits | `create_public_order()` | — | PENDING_OPERATOR_REVIEW |
| Operator approves | `status_machine.approve_public_order()` | PENDING | NEW or WAITING_SERVICE |
| Supplier assigned | `status_machine.assign_supplier()` | NEW | WAITING_SERVICE |
| Service begins | `status_machine.start_order()` | WAITING_SERVICE | IN_PROGRESS |
| Service completes | `status_machine.complete_order()` | IN_PROGRESS | COMPLETED |
| Cancel requested | `status_machine.request_cancellation()` | any non-terminal | CANCELLATION_REQUESTED |
| Cancel approved | `status_machine.approve_cancellation()` | CANCELLATION_REQUESTED | CANCELLED |

**Models:** Order, OrderStatusHistory, ServiceCategory, ServiceType

**Services:** `orders/services/order_creation.py`, `orders/services/status_machine.py`

**Permissions:** **NONE** — status_machine functions have no PermissionService.require() calls (known gap)

**Audit Events:** Status transitions recorded in OrderStatusHistory

**Transaction:** Each transition is atomic with select_for_update on Order row

**Tests:** `orders/tests/test_order_creation.py`, `orders/tests/test_status_machine.py`

---

## 6. Offer Workflow

**Purpose:** Suppliers submit price/terms offers on orders. Currently partially implemented (Sprint 5.1: submit/edit/withdraw only).

**Actors:** Caregiver/Organization supplier

**State Machine:**

```
SUBMITTED → SELECTED → ACCEPTED (terminal)
         → WITHDRAWN (terminal)
         → REJECTED (terminal)
         → CANCELLED (terminal)
         → EXPIRED (terminal)
```

**Implemented (Sprint 5.1):**

| Step | Function | From | To |
|---|---|---|---|
| Submit offer | `OrderOfferService.submit_offer()` | — | SUBMITTED |
| Edit offer | `OrderOfferService.edit_offer()` | SUBMITTED | SUBMITTED (fields updated) |
| Withdraw offer | `OrderOfferService.withdraw_offer()` | SUBMITTED | WITHDRAWN |

**Not Yet Implemented:** select_offer, accept_offer, expire_held_offers, cancel_offers_for_order

**Models:** OrderOffer

**Services:** `orders/services/order_offer_service.py`

**Permissions:** `orders.offer.submit` (submit only); edit/withdraw use ownership check

**Audit Events:** `orders.offer.submitted`, `orders.offer.edited`, `orders.offer.withdrawn`

**Transaction:** Atomic; Order row locked (select_for_update) before offer creation; OrderOffer row locked for edit/withdraw

**Constraints:** One offer per (order, supplier) — DB UniqueConstraint

**Tests:** `orders/tests/test_order_offer_service.py` (29 tests)

---

## 7. Assignment Workflow

**Purpose:** Bind a specific supplier to an order.

**Actors:** Platform operator, Organization admin, Matching engine

**State Machine:**

```
PROPOSED → ASSIGNED → CONFIRMED | DECLINED | REPLACED | CANCELLED | EXPIRED
```

**Execution Steps:**

1. Matching runs → `MatchOrchestrator.run()` → MatchRound + MatchCandidates
2. Assignment created → `AssignmentService.assign()` → SupplierAssignment(ASSIGNED) + Order.assigned_supplier set
3. Provider confirms → `ProviderAssignmentActionService.confirm()` → CONFIRMED
4. Provider declines → `ProviderAssignmentActionService.decline()` → DECLINED

**Models:** SupplierAssignment, MatchRound, MatchCandidate

**Services:** `booking/services/assignment_service.py`, `booking/services/provider_actions.py`, `matching/services/__init__.py`

**Permissions:** `booking.assignment.assign`

**Transaction:** Atomic; Order row locked

**Tests:** `booking/tests/test_assignment.py`, `booking/tests/test_concurrency.py`, `matching/tests/`

---

## 8. Execution Workflow

**Purpose:** Track actual service delivery sessions.

**Actors:** Assigned caregiver, Customer

**State Machine:**

```
SCHEDULED → IN_PROGRESS → PROVIDER_COMPLETED → CUSTOMER_PENDING → CLOSED
                        → PAUSED → IN_PROGRESS (resume)
                        → INTERRUPTED
```

**Models:** ExecutionSession

**Services:** `execution/services/session_service.py`

**Permissions:** `execution.session.close` (for closing sessions)

**Tests:** `execution/tests/`

---

## 9. Financial Pipeline

**Purpose:** Pre-service payment collection, escrow holding, and post-service settlement.

**Execution Steps:**

1. Payment gate activated → `PreServicePaymentService.initiate()` → PaymentDeadline + PaymentIntent
2. Customer pays → `PaymentCallbackService` → PaymentIntent(SUCCEEDED)
3. Escrow funded → `EscrowService.create_escrow_record()` → EscrowRecord(HELD)
4. Commission snapshot frozen → `CommissionSnapshot` created
5. Service completed → ObjectionPeriod created
6. Objection expires → ReleaseInstruction created (PENDING)
7. **GAP: No consumer wires ReleaseInstruction → wallet credit**

**Dispute Path:**
- Customer disputes → `DisputeService.open()` → Dispute(OPEN)
- Platform resolves → `DisputeResolutionService.resolve()` → partial release/refund

**Models:** PaymentIntent, PaymentAttempt, PaymentCallback, EscrowRecord, EscrowMovement, CommissionSnapshot, PaymentDeadline, ObjectionPeriod, Dispute, ReleaseInstruction, RefundInstruction

**Services:** `commission/services/preservice_payment_service.py`, `commission/services/escrow_integration_service.py`, `commission/services/objection_service.py`, `commission/services/dispute_service.py`, `finance/services/escrow_service.py`, `payments/services/`

**Known Gaps:**
- ReleaseInstruction never reaches CONSUMED (no wallet-crediting consumer)
- AllocationCalculator has zero production callers
- Only FakePaymentProvider exists

**Tests:** `commission/tests/`, `finance/tests/`, `payments/tests/`

---

## 10. Company-Caregiver Affiliation

**Purpose:** Manage the employment/contracting relationship between organizations and caregivers.

**Actors:** Company admin, Caregiver

**Execution Steps:**

Join by code:
1. Caregiver enters code → `affiliations.submit_join_request()` → Request(PENDING)
2. Company approves → `affiliations.approve_affiliation_request()` → Membership(ACTIVE)

Invitation:
1. Company invites → `affiliations.invite_caregiver()` → Membership(PENDING)
2. Caregiver accepts → `affiliations.accept_invitation()` → Membership(ACTIVE)

Termination:
- Company terminates → `affiliations.terminate_membership()`
- Caregiver leaves → `affiliations.leave_organization()`
- Both produce terminal membership rows (immutable history; new row on rejoin)

**Constraint:** One active company per caregiver at a time (CaregiverProfile row locked for enforcement)

**Models:** OrganizationMembership, CompanyAffiliationRequest

**Services:** `accounts/services/affiliations.py`

**Permissions:** `organization.membership.invite`, `.reject`, `.terminate`, `.approve`

**Tests:** `accounts/tests/test_affiliation_lifecycle.py`

---

## 11. Notification Workflow

**Purpose:** Deliver cross-channel notifications for domain events.

**Actors:** System (automated)

**Execution Steps:**

1. Domain event occurs → `EventPublisher.publish()` → EventOutbox row
2. Celery task → `publish_outbox_events()` → dispatches events to consumers
3. Consumer creates Notification row
4. `NotificationDispatchService.dispatch_pending()` → attempts delivery (SMS/email/push/in-app)
5. Delivery recorded → NotificationDeliveryAttempt

**Models:** Notification, NotificationDeliveryAttempt, EventOutbox

**Services:** `notifications/services/dispatch_service.py`, `kernel/services/event_publisher.py`, `kernel/tasks.py`

**Known Gap:** No real SMS/email provider integrated. Notifications are created but not delivered externally.

**Tests:** `notifications/tests/`

---

## 12. Reviews and Reputation

**Purpose:** Customer reviews of completed services; aggregate reputation scores.

**Actors:** Customer (reviewer), Platform moderator

**Execution Steps:**

1. Order completed → review eligible
2. Customer submits → `ReviewSubmissionService.submit()` → Review(PENDING)
3. Moderator approves → `ReviewModerationService.approve()` → Review(APPROVED)
4. Reputation recalculated → `ReputationService.recalculate()` → ReputationSnapshot updated

**Models:** Review, ReviewRating, ReputationSnapshot

**Services:** `reviews/services/`

**Permissions:** `reviews.submit`, `reviews.read`

**Tests:** `reviews/tests/`

---

## State Machine Summary

| Entity | States | Terminal States | Source |
|---|---|---|---|
| Order | 7 | completed, cancelled | `orders/services/status_machine.py` |
| OrderOffer | 7 | accepted, expired, withdrawn, rejected, cancelled | `orders/services/order_offer_service.py` |
| Profile | 4 | (none — no deactivation service) | `accounts/services/profile_activation_service.py` |
| VerificationDocument | 4 | verified | `accounts/services/verification_review_service.py` |
| SupplierAssignment | 7 | confirmed, declined, replaced, cancelled, expired | `booking/services/assignment_service.py` |
| ExecutionSession | 7 | closed | `execution/services/session_service.py` |
| PaymentIntent | 7 | succeeded, failed, cancelled, expired | `payments/services/payment_intent_service.py` |
| EscrowRecord | 9 | closed, cancelled | `finance/services/escrow_service.py` |
| FinancialDocument | 7 | paid, voided, cancelled | `finance/services/document_service.py` |
