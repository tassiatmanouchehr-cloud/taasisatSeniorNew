# OFFER MARKETPLACE — REVISED IMPLEMENTATION CONTRACT

**Scope:** Offer Marketplace epic only.
**Source of truth:** Current repository at commit `a5dbaf28703142edaa1d770ea8f3c2a45a12640f`.
**Baseline:** 1632 tests passing, PostgreSQL.

---

## 1. Final Semantic Decisions

### 1.1 No Separate Reservation Table

`OrderOffer.SELECTED` **is** the temporary 30-minute hold. There is no separate reservation model. The hold is a status on the offer itself, augmented by `hold_expires_at` and `selected_at` timestamp fields on `OrderOffer`. When the hold is active:
- The offer is in `SELECTED` status
- A `SupplierAssignment` exists with `assignment_source=OFFER`
- `Order.assigned_supplier` points to the offer's supplier
- `Order.status` is `WAITING_SERVICE`
- A `PaymentDeadline` tracks the 30-minute window

### 1.2 Assignment Timing: Option B — After Successful Payment

**Decision: Do NOT create SupplierAssignment at offer selection. Create it only after successful payment.**

Rationale from tracing every side effect of `AssignmentService.assign()`:

| Side Effect | Line | Impact if created at selection | Impact if created at payment |
|------------|------|-------------------------------|------------------------------|
| `Order.status → WAITING_SERVICE` | status_machine.py:70 | Order leaves NEW immediately; other caregivers see it as taken | Order stays NEW until payment confirms; offer hold is tracked on OrderOffer only |
| `Order.assigned_supplier = supplier` | status_machine.py:69 | Provider appears as "assigned" before payment | Provider assigned only when payment is confirmed |
| Provider confirm/decline possible | provider_actions.py:43 | Provider could confirm/decline an unconfirmed booking | Provider acts only after payment |
| Capacity counted | capacity_service.py:45 | Supplier's capacity reduced during hold | Capacity reduced only on confirmed booking |
| Commission snapshot created | snapshot_service.py:41 | Snapshot frozen before payment; amount unknown | Snapshot created with known payment amount |
| Payment deadline created | deadline_service.py:61 | **Redundant** — we already have hold_expires_at on OrderOffer | Not needed — OrderOffer hold replaces deadline |
| Pre-service invoice + PaymentIntent created | assignment_service.py:187 | Creates intent before selection is confirmed | Intent created after selection, cleaner flow |
| Notification sent to customer | handlers.py:70 | "Order Assigned" notification before payment | Notification after payment confirms |
| `Booking.Assignment.Created.v1` event | assignment_service.py:125 | Event fired for unconfirmed booking | Event fired for confirmed booking |
| ExecutionSession requires ASSIGNED/CONFIRMED | session_service.py:60 | Provider could try to start execution before payment | Execution starts only after payment |

**Option B is safer** because:
1. No premature status change — order stays NEW during the hold
2. No premature capacity reduction — supplier isn't locked during hold
3. No premature notification — customer isn't notified until payment confirms
4. No premature provider actions — provider can't confirm/decline during hold
5. Cleaner financial flow — commission snapshot and deadline created at the right time

**How the hold is enforced without SupplierAssignment:** The `OrderOffer` model with `status=SELECTED` and `hold_expires_at` is the hold. The expiry handler transitions the offer to EXPIRED and the order remains NEW. No assignment exists to expire.

### 1.3 Selection Policy: One Active Hold Per Order

**Unambiguous policy:**
- Selecting the **same offer** twice → **idempotent no-op** (returns existing SELECTED offer)
- Selecting a **different offer** while a hold is active → **rejected with error** ("An offer is already being held for this order. Wait for the hold to expire or cancel the current selection.")
- A new offer may be selected **only after**: (a) the current hold expires, (b) the customer explicitly cancels the hold, or (c) payment succeeds on the current hold

This eliminates the contradiction. Order status stays NEW during the hold. The "order must be NEW for selection" and "concurrent second selection must fail" are both satisfied because the guard is on OrderOffer status, not Order status.

### 1.4 Payment Failure Does NOT Expire the Selection

When payment fails:
- The PaymentIntent becomes FAILED (terminal)
- The OrderOffer remains SELECTED
- The hold_expires_at continues counting down
- Customer can retry by creating a new PaymentIntent
- Only when hold_expires_at passes without successful payment does the selection expire

### 1.5 Order Status During Hold and Marketplace Visibility

The order stays in `NEW` status during the hold. However, it must NOT appear as freely available to other caregivers.

**Discovery query guard:**

```sql
-- Caregiver marketplace query
SELECT * FROM orders_order
WHERE status = 'new'
  AND NOT EXISTS (
    SELECT 1 FROM orders_orderoffer
    WHERE order_id = orders_order.id
      AND status = 'selected'
  )
```

**Behavior by phase:**

| Phase | Order visible? | New offers allowed? | Existing offers |
|-------|---------------|--------------------|-----------------| 
| Before selection | Yes | Yes | N/A |
| During SELECTED hold | **No** | **No** | Stored, unchanged |
| After hold expiry | Yes | Yes | Previous SUBMITTED offers remain valid |
| After payment success | No (now WAITING_SERVICE) | No | SUBMITTED → REJECTED |
| After order cancellation | No (now CANCELLED) | No | All → CANCELLED |

**Why this matters:** Without the guard, other caregivers could submit offers on an order that is temporarily reserved. The guard is a single `NOT EXISTS` subquery added to the discovery service.

---

## 2. Corrected Domain Model

### New Model: `OrderOffer`

**App:** `apps.orders` (offers are order-scoped)

```python
class OrderOfferStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    SELECTED = "selected", "Selected"       # 30-minute hold active
    ACCEPTED = "accepted", "Accepted"       # Payment succeeded
    EXPIRED = "expired", "Expired"          # Hold timed out
    WITHDRAWN = "withdrawn", "Withdrawn"    # Caregiver withdrew
    REJECTED = "rejected", "Rejected"       # Superseded by another selection
    CANCELLED = "cancelled", "Cancelled"    # Order cancelled while offer was active


class OrderOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("kernel.Tenant", on_delete=models.PROTECT, related_name="order_offers")
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="offers")
    supplier = models.ForeignKey("kernel.ServiceSupplier", on_delete=models.CASCADE, related_name="order_offers")

    # Offer content — aligned with repository money representation
    price_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="IRR")
    estimated_duration_minutes = models.IntegerField(null=True, blank=True)
    terms = models.TextField(blank=True)
    message = models.TextField(blank=True)

    # Lifecycle
    status = models.CharField(
        max_length=20, choices=OrderOfferStatus.choices,
        default=OrderOfferStatus.SUBMITTED, db_index=True,
    )

    # Ownership
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+",
    )

    # Hold tracking (only meaningful when status=SELECTED)
    selected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    selected_at = models.DateTimeField(null=True, blank=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True)

    # NOTE: PaymentIntent → OrderOffer link is on PaymentIntent.order_offer FK (1:many),
    # NOT on OrderOffer.payment_intent FK. One offer may have multiple payment attempts.
    # See Section 6A for the PaymentIntent model change.

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_order_offer"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "supplier"],
                condition=models.Q(status__in=["submitted", "selected"]),
                name="uq_order_offer_one_active_per_supplier",
            ),
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status="selected"),
                name="uq_order_offer_one_selected_per_order",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_offer_tenant_order_st"),
            models.Index(fields=["tenant", "supplier", "status"], name="idx_offer_tenant_supplier_st"),
        ]
```

**Fields NOT included:** `supplier_assignment` FK (removed — assignment is created at payment, not selection). `payment_intent` FK links the offer to its payment attempt.

---

## 3. Corrected State Machines

### 3.1 OrderOffer State Machine

```
                         ┌──────────────┐
                         │   SUBMITTED  │◄──── edit() ────┐
                         └──────┬───────┘                  │
                                │                          │
              ┌─────────────────┼─────────────────┐        │
              │                 │                 │        │
         select()          withdraw()         expire()      │
              │                 │                 │        │
              ▼                 ▼                 ▼        │
       ┌──────────┐      ┌───────────┐      ┌──────────┐  │
       │ SELECTED │      │ WITHDRAWN │      │ EXPIRED  │  │
       └────┬─────┘      └───────────┘      └──────────┘  │
            │                                              │
   ┌────────┼────────────┐                                 │
   │        │            │                                 │
payment_ok  hold_timeout  cancel_order                     │
   │        │            │                                 │
   ▼        ▼            ▼                                 │
┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│ ACCEPTED │ │ EXPIRED  │ │CANCELLED │                     │
└──────────┘ └──────────┘ └──────────┘                     │
                                                           │
REJECTED (set in bulk on other SUBMITTED offers            │
         when payment succeeds) ───────────────────────────┘
```

**Transition rules:**

| From | To | Trigger | Guard |
|------|-----|---------|-------|
| SUBMITTED | SUBMITTED | `edit()` | Actor owns supplier, all fields valid |
| SUBMITTED | WITHDRAWN | `withdraw()` | Actor owns supplier |
| SUBMITTED | EXPIRED | `expire()` | Another offer on same order was selected |
| SUBMITTED | SELECTED | `select()` | Order is NEW, no other offer is SELECTED on this order, actor owns customer_profile |
| SUBMITTED | CANCELLED | `cancel_order()` | Order entered CANCELLED status |
| SELECTED | ACCEPTED | `confirm_payment()` | PaymentIntent status is SUCCEEDED |
| SELECTED | EXPIRED | `expire_hold()` | hold_expires_at has passed |
| SELECTED | CANCELLED | `cancel_order()` | Order entered CANCELLED status |

**REJECTED semantics (post-payment bulk operation):**
- REJECTED is NOT a direct transition from SELECTED
- REJECTED is set in bulk by `confirm_payment()` on all other SUBMITTED offers for the same order
- A SUBMITTED offer becomes REJECTED only when another offer on the same order is ACCEPTED
- A SUBMITTED offer that was present during a hold expiry remains SUBMITTED (not REJECTED)

**CANCELLED semantics:**
- CANCELLED applies to all active offers (SUBMITTED and SELECTED) when the order is cancelled
- This is a bulk operation triggered by order cancellation

### 3.2 Order Status During Offer Flow

```
NEW ──(offer selected)──> NEW          # Order stays NEW during hold
NEW ──(payment succeeds)──> WAITING_SERVICE  # Only now does status change
NEW ──(hold expires)──> NEW            # No change needed
WAITING_SERVICE ──(start)──> IN_PROGRESS     # Existing flow
```

**Key difference from current flow:** Order status changes to WAITING_SERVICE only on payment success, not at selection.

### 3.3 SupplierAssignment in Offer Flow

No new statuses. The assignment is created only when payment succeeds:

```
Payment succeeds → AssignmentService.assign(source=OFFER) → ASSIGNED
Provider confirms → CONFIRMED (existing flow)
Provider declines → DECLINED (existing flow)
```

---

## 4. Assignment Timing Decision

**Option B: Create SupplierAssignment only after successful payment.**

This means `AssignmentService.assign()` is NOT called at selection time. Instead:

1. Customer selects offer → `OrderOffer` status → SELECTED, `hold_expires_at` set
2. Customer initiates payment → `PaymentIntent` created, linked to offer via `payment_intent` FK
3. Payment succeeds → `OrderOffer` status → ACCEPTED, then `AssignmentService.assign()` called
4. Assignment creates SupplierAssignment, sets Order.assigned_supplier, Order.status → WAITING_SERVICE
5. All side effects (commission snapshot, deadline, notification, event) fire at this point

**What changes in AssignmentService:** Nothing. The service is called with the same parameters, just at a different time.

**What changes in the order flow:** The `OrderOfferService.select_offer()` method does NOT call `AssignmentService.assign()`. It only updates the OrderOffer. The wiring layer (event handler or explicit call) calls `AssignmentService.assign()` when payment succeeds.

---

## 5. Transaction Boundaries

### 5.1 `OrderOfferService.submit_offer()`

```
@transaction.atomic
def submit_offer(...):
    # 1. Lock and validate Order (select_for_update)
    # 2. Check eligibility
    # 3. Upsert OrderOffer (get_or_create with IntegrityError handling)
    # 4. Publish OrderOfferSubmitted event
    return offer
```

### 5.2 `OrderOfferService.select_offer()`

```
@transaction.atomic
def select_offer(...):
    # 1. Lock Order (select_for_update)
    # 2. Verify order.status == NEW
    # 3. Check no other offer is SELECTED on this order
    # 4. Lock the target OrderOffer (select_for_update)
    # 5. Verify offer.status == SUBMITTED
    # 6. Update offer: status→SELECTED, selected_by, selected_at, hold_expires_at
    # 7. Publish OrderOfferSelected event
    return offer
```

### 5.3 `OrderOfferService.confirm_payment()`

```
@transaction.atomic
def confirm_payment(*, offer_id, payment_intent_id):
    # 1. Lock Order (select_for_update)
    # 2. Lock OrderOffer (select_for_update)
    # 3. Fetch PaymentIntent, verify exists
    # 4. Validate: tenant match, intent belongs to offer, intent belongs to order
    # 5. Validate: intent.status == SUCCEEDED
    # 6. Validate: offer.status == SELECTED, hold not expired
    # 7. Validate: amount and currency match offer
    # 8. Validate: no prior SUCCEEDED intent already finalized this offer
    # 9. Update offer: status→ACCEPTED
    # 10. Bulk update: all other SUBMITTED offers for same order → REJECTED
    # 11. Mark PaymentDeadline as COMPLETED (via PaymentDeadlineService.mark_completed)
    # 12. Call AssignmentService.assign() with source=OFFER
    #     (this internally locks Order and creates SupplierAssignment)
    # 13. Publish OrderOfferAccepted event
    return offer
```

### 5.4 `OrderOfferService.expire_hold()`

```
@transaction.atomic
def expire_hold(...):
    # 1. Lock OrderOffer (select_for_update)
    # 2. Verify offer.status == SELECTED
    # 3. Verify hold_expires_at has passed
    # 4. Update offer: status→EXPIRED
    # 5. No Order mutation needed (order stays NEW)
    # 6. Publish OrderOfferExpired event
    return offer
```

---

## 6A. PaymentIntent → OrderOffer Link (RISK-004 Resolution)

### Cardinality

One `OrderOffer` may be linked to **many** `PaymentIntent` records (1:N). Each retry creates a new intent. Only the successful intent finalizes the offer.

### PaymentIntent Model Change

Add a nullable `order_offer` FK to `PaymentIntent`:

```python
# In apps/payments/models.py, add to PaymentIntent:
order_offer = models.ForeignKey(
    "orders.OrderOffer",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="payment_intents",
    help_text="Links this payment attempt to a specific OrderOffer selection.",
)
```

**Migration impact:** Single `ALTER TABLE` adding nullable FK. No data migration needed.

### confirm_payment Signature

```python
@classmethod
@transaction.atomic
def confirm_payment(
    cls,
    *,
    offer_id: uuid.UUID,
    payment_intent_id: uuid.UUID,
) -> OrderOffer:
```

### Required Validation (in order)

1. **Lock Order** (`select_for_update`) — serializes concurrent operations
2. **Lock OrderOffer** (`select_for_update`) — serializes concurrent payment callbacks
3. **Fetch PaymentIntent** — verify it exists
4. **Tenant match** — `intent.tenant_id == offer.tenant_id`
5. **Intent belongs to offer** — `intent.order_offer_id == offer.id`
6. **Intent belongs to same order** — `intent.reference_id == offer.order_id` (or verify via order relationship)
7. **Intent status is SUCCEEDED** — reject FAILED/CREATED/PENDING/EXPIRED/CANCELLED
8. **Offer status is SELECTED** — reject if already ACCEPTED, EXPIRED, WITHDRAWN, REJECTED, CANCELLED
9. **Hold not expired** — `offer.hold_expires_at > timezone.now()` (defensive, even though expired offers should already be EXPIRED)
10. **Amount matches** — `intent.amount == offer.price_amount`
11. **Currency matches** — `intent.currency == offer.currency`
12. **No prior successful intent** — check no other SUCCEEDED intent already finalized this offer (idempotency guard)

### Idempotency Rules

| Scenario | Behavior |
|----------|----------|
| Same successful intent called twice | No-op (step 12 catches duplicate) |
| Second successful intent after first already accepted | Rejected at step 12 (exactly one ACCEPTED) |
| Failed intent then successful retry | First call rejected (FAILED), second succeeds |
| Callback after hold expiry | Rejected at step 8 (offer is EXPIRED) |
| Callback for wrong offer | Rejected at step 5 |
| Callback from cross-tenant intent | Rejected at step 4 |
| Amount mismatch | Rejected at step 10 |
| Currency mismatch | Rejected at step 11 |

### Race Handling

```
Lock acquisition order:
1. Order (select_for_update) — serializes concurrent selections
2. OrderOffer (select_for_update) — serializes concurrent payment callbacks
3. PaymentIntent — read-only validation (no lock needed; intent status is terminal)
```

**Success at expiry boundary:** If `intent.status == SUCCEEDED` and `offer.hold_expires_at <= now()`, the offer is already EXPIRED (set by the expiry job). The confirm_payment call sees `offer.status == EXPIRED` at step 8 and rejects. The successful payment is not lost — it remains recorded as a SUCCEEDED PaymentIntent, but the offer is expired. The customer would need to re-select and re-pay.

### Data Model Impact

| Model | Change |
|-------|--------|
| `OrderOffer` | Remove `payment_intent` FK (was 1:1, now 1:N via PaymentIntent.order_offer) |
| `PaymentIntent` | Add nullable `order_offer` FK |

### Files Changed

| File | Change |
|------|--------|
| `apps/orders/models.py` | Remove `payment_intent` FK from OrderOffer |
| `apps/payments/models.py` | Add `order_offer` FK to PaymentIntent |
| `apps/payments/migrations/NNNN_add_order_offer_fk.py` | New migration |

### Tests Required

| Test | Type | What It Verifies |
|------|------|-----------------|
| `test_failed_then_successful_retry` | TransactionTestCase | Failed intent rejected, successful retry accepted |
| `test_stale_failed_callback` | TransactionTestCase | FAILED intent cannot finalize offer |
| `test_two_successful_callbacks` | TransactionTestCase | Second SUCCEEDED intent rejected (idempotency) |
| `test_callback_after_hold_expiry` | TransactionTestCase | Expired offer rejects payment |
| `test_wrong_offer_intent` | TransactionTestCase | Intent for different offer rejected |
| `test_cross_tenant_intent` | TransactionTestCase | Cross-tenant intent rejected |
| `test_amount_mismatch` | TransactionTestCase | Amount mismatch rejected |
| `test_currency_mismatch` | TransactionTestCase | Currency mismatch rejected |
| `test_repeated_callback_idempotency` | TransactionTestCase | Same callback twice is no-op |
| `test_concurrent_callbacks_exactly_one_assignment` | TransactionTestCase + threading | Two concurrent callbacks produce exactly one ACCEPTED + one SupplierAssignment |

---

## 6. Lock Ordering

**Consistent lock acquisition order:**

1. `Order` (when needed) — first
2. `OrderOffer` — second

This matches the existing pattern in `AssignmentService.assign()` which locks Order first, then creates/modifies SupplierAssignment.

**Specific scenarios:**

| Operation | Lock Order? | Lock OrderOffer? | Notes |
|-----------|------------|-------------------|-------|
| submit_offer | Yes (validate status) | No (get_or_create with constraint) | IntegrityError handles race |
| edit_offer | No | Yes | Only modifies offer fields |
| withdraw_offer | No | Yes | Only modifies offer status |
| select_offer | Yes | Yes | Order first, then offer |
| confirm_payment | No | Yes | Order lock inside AssignmentService.assign() |
| expire_hold | No | Yes | Only modifies offer status |

---

## 7. Authorization Enforcement

Authorization is enforced **inside service methods**, not only in portal views.

### 7.1 `submit_offer()`

```python
def submit_offer(cls, *, ..., supplier: ServiceSupplier, submitted_by: UserAccount, ...):
    # Inside the service:
    if supplier.tenant_id != order.tenant_id:
        raise OrderOfferError("Supplier tenant does not match order tenant.")
    if supplier.status != SupplierStatus.ACTIVE:
        raise OrderOfferError("Supplier must be ACTIVE to submit offers.")
    # Caller must own the supplier (enforced at view layer via resolve_supplier_for_user,
    # but also verified here for API callers):
    if not _supplier_owned_by(supplier, submitted_by):
        raise OrderOfferError("Actor does not own this supplier.")
```

### 7.2 `select_offer()`

```python
def select_offer(cls, *, ..., customer_user: UserAccount, ...):
    # Inside the service:
    if not _order_owned_by(order, customer_user):
        raise OrderOfferError("Actor does not own this order.")
    # Tenant isolation enforced by TenantScopedManager
```

### 7.3 `edit_offer()` / `withdraw_offer()`

```python
def edit_offer(cls, *, ..., actor: UserAccount, ...):
    if not _supplier_owned_by(offer.supplier, actor):
        raise OrderOfferError("Actor does not own this offer.")
```

**Helper functions:**

```python
def _supplier_owned_by(supplier: ServiceSupplier, user: UserAccount) -> bool:
    """Verify the user owns this supplier via the supplier_bridge."""
    from apps.accounts.services.supplier_bridge import resolve_supplier_for_user
    try:
        owned = resolve_supplier_for_user(user)
        return owned.id == supplier.id
    except Exception:
        return False

def _order_owned_by(order: Order, user: UserAccount) -> bool:
    """Verify the user owns this order's customer_profile."""
    from apps.portal.permissions import resolve_customer_profile
    try:
        profile = resolve_customer_profile(user)  # adapted for service context
        return order.customer_profile_id == profile.id
    except Exception:
        return False
```

---

## 8. Money Representation

**Canonical:** `DecimalField(max_digits=14, decimal_places=2)`, `DEFAULT_CURRENCY = "IRR"`.

This is consistent across: Quote, FinancialDocument, FinancialDocumentItem, PaymentIntent, Wallet, WalletTransaction, CommissionSnapshot.

**OrderOffer uses the same representation:**

```python
price_amount = models.DecimalField(max_digits=14, decimal_places=2)
currency = models.CharField(max_length=10, default="IRR")
```

**NOT using integer IRR** (which is reserved for EscrowRecord PR-B fields and AllocationCalculator). The offer price is a customer-facing monetary amount, matching the Quote/FinancialDocument pattern.

---

## 9. Event/Orchestration Wiring

### 9.1 New Domain Events

| Event Type | Published By | Handler |
|-----------|-------------|---------|
| `OrderOfferSubmitted` | `OrderOfferService.submit_offer()` | None (audit only) |
| `OrderOfferSelected` | `OrderOfferService.select_offer()` | None (audit only) |
| `OrderOfferAccepted` | `OrderOfferService.confirm_payment()` | Triggers `AssignmentService.assign()` |
| `OrderOfferExpired` | `OrderOfferService.expire_hold()` | None (order stays NEW) |
| `OrderOfferWithdrawn` | `OrderOfferService.withdraw_offer()` | None (audit only) |
| `OrderOfferRejected` | `OrderOfferService.select_offer()` | None (audit only) |

### 9.2 Wiring: Payment Success → Assignment

The critical wiring is: **when payment succeeds, call `confirm_payment()` which calls `AssignmentService.assign()`.**

This is wired in `SettlementOrchestrationService.settle_payment_intent()` or `PaymentCallbackService._trigger_settlement()`. The exact insertion point:

```python
# In PaymentCallbackService._trigger_settlement(), after settlement succeeds:
if intent.status == PaymentStatus.SUCCEEDED:
    # Check if this intent is linked to an OrderOffer
    from apps.orders.services.offer_service import OrderOfferService
    offer = OrderOffer.objects.filter(payment_intent=intent, status=OrderOfferStatus.SELECTED).first()
    if offer:
        OrderOfferService.confirm_payment(offer_id=offer.id)
```

**Alternative: explicit orchestration in the portal view** (simpler, no service modification):

```python
# In portal request_financial_pay_view, after fake payment succeeds:
if outcome == "SUCCEEDED":
    OrderOfferService.confirm_payment(offer_id=selected_offer.id)
```

### 9.3 Wiring: Payment Failure → No Action

Payment failure does NOT trigger any offer state change. The offer remains SELECTED. The hold_expires_at continues counting down.

### 9.4 Wiring: Hold Expiry (PaymentDeadline Reuse)

The existing `PaymentDeadline` infrastructure is reused for the offer hold. No separate deadline engine is created.

**Compatibility proof:**

| Aspect | PaymentDeadline | OrderOffer Hold | Compatible? |
|--------|----------------|-----------------|-------------|
| Fields | tenant, order, assignment (nullable), deadline_at, status, expiry_job_id | tenant, order, hold_expires_at | Yes — assignment FK is nullable |
| Statuses | PENDING, COMPLETED, EXPIRED, CANCELLED | PENDING → COMPLETED/EXPIRED/CANCELLED | Yes — same lifecycle |
| Expiry logic | `expire_due()` checks `status==PENDING` and `deadline_at <= now()` | Same check works for hold_expires_at | Yes — identical guard |
| Cascade | Calls `AssignmentService.expire(order_id=...)` | Needs `OrderOfferService.expire_hold(offer_id=...)` | **Requires routing change** |
| Scheduler | `JobService.enqueue()` with retry | Same infrastructure | Yes — reuse existing |
| Audit | `AuditService.log()` on every transition | Same pattern | Yes — reuse existing |
| Feature gate | `commission.payment_deadline.activation_enabled` | New gate: `orders.offer_hold.activation_enabled` | Yes — separate gate |
| Idempotency | `expire_due()` is idempotent (no-op if not PENDING) | Same behavior needed | Yes — same pattern |

**Required changes to PaymentDeadline:**
1. Add nullable `order_offer` FK: `models.ForeignKey("orders.OrderOffer", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_deadlines")`
2. In `expire_due()`, add routing: if `deadline.order_offer_id` is set, call `OrderOfferService.expire_hold(offer_id=deadline.order_offer_id)`; else call `AssignmentService.expire(order_id=deadline.order_id)` (existing behavior)

**Deadline creation:** `PaymentDeadlineService.create_for_offer(offer, hold_seconds=1800)` — new method that creates a PENDING deadline with `order_offer` set and `assignment` null.

**Deadline completion:** On payment success, `PaymentDeadlineService.mark_completed(order_id=offer.order_id)` — existing method, transitions PENDING → COMPLETED.

**Files modified:**
- `apps/commission/models/deadline.py` — add nullable `order_offer` FK
- `apps/commission/services/deadline_service.py` — add `create_for_offer()` method, add routing in `expire_due()`

**Why no duplicate engine:** PaymentDeadline already has scheduler integration, retry logic, idempotent expiry, audit logging, and feature gates. Extending it with a nullable FK and routing change is safer than building a parallel system.

### 9.5 Wiring: Order Cancellation

When an order is cancelled (via `approve_cancellation()`), all active offers must be transitioned to CANCELLED. This is wired in the status machine or as a post-cancellation handler:

```python
# In status_machine.py, after approve_cancellation():
from apps.orders.services.offer_service import OrderOfferService
OrderOfferService.cancel_all_for_order(order_id=order.id)
```

### 9.6 Registration Pattern

New event handlers are registered in `apps.orders.apps.OrdersConfig.ready()`, following the same pattern as `apps.notifications.apps.NotificationsConfig.ready()`.

---

## 10. Database Constraints

### 10.1 Constraints on OrderOffer

| Constraint | Type | Fields | Condition | Purpose |
|-----------|------|--------|-----------|---------|
| `uq_order_offer_one_active_per_supplier` | UniqueConstraint | (order, supplier) | status IN ('submitted', 'selected') | One active offer per caregiver per order |
| `uq_order_offer_one_selected_per_order` | UniqueConstraint | (order) | status = 'selected' | One selected offer per order |

### 10.2 Why Conditional, Not Unconditional

An unconditional `UniqueConstraint(order, supplier)` would prevent a caregiver from submitting a new offer after withdrawing an old one on the same order. The conditional constraint allows:
- Submit → Withdraw → Submit again (allowed)
- Submit → Expired → Submit again (allowed)
- Submit → Accepted → no new offer (blocked by ACCEPTED not in the condition)

### 10.3 Why Not Just One Active Constraint

The two constraints serve different purposes:
1. One active per supplier: prevents duplicate offers from the same caregiver
2. One selected per order: prevents two simultaneous holds on the same order

Both are needed. The first prevents data corruption; the second enforces business policy.

---

## 11. Failure and Retry Behavior

### 11.1 Payment Failure While Hold Active

```
Payment fails → PaymentIntent.status = FAILED (terminal)
               → OrderOffer.status stays SELECTED
               → hold_expires_at continues counting down
               → Customer can retry (create new PaymentIntent)
```

### 11.2 Payment Retry

```
Customer retries → New PaymentIntent created for same order
                 → New PaymentAttempt started
                 → If succeeds → OrderOffer → ACCEPTED → AssignmentService.assign()
                 → If fails → Same as 11.1
```

### 11.3 Hold Expiry Without Payment

```
hold_expires_at passes → Job fires → OrderOfferService.expire_hold()
                       → OrderOffer.status → EXPIRED
                       → No Order mutation (order stays NEW)
                       → Order remains available for new offers
```

### 11.4 Caregiver Withdraws During Hold

**Not allowed.** `withdraw_offer()` only accepts SUBMITTED offers. An offer in SELECTED status cannot be withdrawn by the caregiver. The only ways to release a hold are:
1. Payment succeeds (→ ACCEPTED)
2. Hold expires (→ EXPIRED)
3. Customer cancels the order (→ CANCELLED)

### 11.5 Customer Cancels Order During Hold

```
Customer cancels → Order status → CANCELLATION_REQUESTED → CANCELLED
                → OrderOffer → CANCELLED (wired in cancel path)
```

### 11.6 Offer State After Each Event

| Event | Selected Offer | Other SUBMITTED Offers | Order Status |
|-------|---------------|----------------------|--------------|
| Customer selects offer A | A → SELECTED | Unchanged | NEW |
| Payment succeeds on A | A → ACCEPTED | → EXPIRED | → WAITING_SERVICE |
| Hold expires on A | A → EXPIRED | Unchanged | NEW |
| Customer cancels order | A → CANCELLED | → CANCELLED | → CANCELLED |
| Customer selects offer B while A is SELECTED | **Rejected** (error) | Unchanged | NEW |

---

## 12. PostgreSQL Test Strategy

All tests use the real PostgreSQL ORM. No mocked databases.

### 12.1 Model Tests

| Test | Type | What It Verifies |
|------|------|-----------------|
| `test_order_offer_creation` | TransactionTestCase | OrderOffer creation with all fields, default status=SUBMITTED |
| `test_order_offer_unique_active_per_supplier` | TransactionTestCase | Second SUBMITTED offer from same supplier raises IntegrityError |
| `test_order_offer_unique_selected_per_order` | TransactionTestCase | Second SELECTED offer on same order raises IntegrityError |
| `test_order_offer_withdraw_allows_resubmit` | TransactionTestCase | Submit → Withdraw → Submit again succeeds |
| `test_order_offer_expired_allows_resubmit` | TransactionTestCase | Submit → Expired → Submit again succeeds |
| `test_order_offer_accepted_blocks_new_offer` | TransactionTestCase | Submit → Accepted → new offer from same supplier raises IntegrityError |

### 12.2 Service Tests

| Test | Type | What It Verifies |
|------|------|-----------------|
| `test_submit_offer_valid` | TransactionTestCase | Happy path: order NEW, supplier ACTIVE, offer created |
| `test_submit_offer_rejects_non_new_order` | TransactionTestCase | Order in WAITING_SERVICE raises error |
| `test_submit_offer_rejects_inactive_supplier` | TransactionTestCase | Supplier in SUSPENDED raises error |
| `test_submit_offer_rejects_wrong_tenant` | TransactionTestCase | Supplier from different tenant raises error |
| `test_edit_offer_valid` | TransactionTestCase | Fields updated, status stays SUBMITTED |
| `test_edit_offer_rejects_non_submitted` | TransactionTestCase | Editing SELECTED offer raises error |
| `test_edit_offer_rejects_wrong_owner` | TransactionTestCase | Different supplier's actor raises error |
| `test_withdraw_offer_valid` | TransactionTestCase | SUBMITTED → WITHDRAWN |
| `test_withdraw_offer_rejects_selected` | TransactionTestCase | WITHDRAWING SELECTED offer raises error |
| `test_select_offer_valid` | TransactionTestCase | SUBMITTED → SELECTED, hold_expires_at set |
| `test_select_offer_rejects_non_new_order` | TransactionTestCase | Order not in NEW raises error |
| `test_select_offer_rejects_already_selected` | TransactionTestCase | Another offer already SELECTED raises error |
| `test_select_offer_idempotent` | TransactionTestCase | Selecting same offer twice is no-op |
| `test_select_offer_rejects_wrong_owner` | TransactionTestCase | Non-owner raises error |
| `test_confirm_payment_valid` | TransactionTestCase | SELECTED → ACCEPTED, SupplierAssignment created, Order.status → WAITING_SERVICE |
| `test_confirm_payment_rejects_expired_hold` | TransactionTestCase | Hold expired raises error |
| `test_expire_hold_valid` | TransactionTestCase | SELECTED → EXPIRED, order stays NEW |
| `test_expire_hold_rejects_not_yet_due` | TransactionTestCase | hold_expires_at in future raises error |
| `test_cancel_all_for_order` | TransactionTestCase | All active offers → CANCELLED |

### 12.3 Concurrency Tests

| Test | Type | What It Verifies |
|------|------|-----------------|
| `test_concurrent_select_same_offer` | TransactionTestCase + threading | Two threads selecting same offer → one succeeds, one gets idempotent result |
| `test_concurrent_select_different_offers` | TransactionTestCase + threading | Two threads selecting different offers on same order → exactly one succeeds |
| `test_concurrent_submit_same_supplier` | TransactionTestCase + threading | Two threads submitting from same supplier → IntegrityError on one |
| `test_concurrent_select_and_withdraw` | TransactionTestCase + threading | Thread A selects while Thread B withdraws → one wins, other gets error |

### 12.4 Integration Tests

| Test | Type | What It Verifies |
|------|------|-----------------|
| `test_full_offer_flow_submit_select_pay` | TransactionTestCase | End-to-end: submit → select → payment success → ACCEPTED → assignment created |
| `test_full_offer_flow_submit_select_expire` | TransactionTestCase | End-to-end: submit → select → hold expires → EXPIRED → order still NEW |
| `test_full_offer_flow_submit_select_fail_retry` | TransactionTestCase | Submit → select → payment fail → retry → payment success |
| `test_full_offer_flow_cancel_order` | TransactionTestCase | Submit → select → order cancelled → offer CANCELLED |

---

## 13. Exact Files That Must Be Modified

### 13.1 New Files

| File | Purpose |
|------|---------|
| `apps/orders/migrations/0008_orderoffer.py` | Database migration |
| `apps/orders/services/offer_service.py` | OrderOfferService |
| `apps/orders/services/discovery_service.py` | OrderDiscoveryService (caregiver order browsing) |
| `apps/orders/tests/test_offer_model.py` | Model tests |
| `apps/orders/tests/test_offer_service.py` | Service tests |
| `apps/orders/tests/test_offer_concurrency.py` | Concurrency tests |
| `apps/orders/tests/test_offer_integration.py` | Integration tests |
| `apps/portal/templates/portal/offers_compare.html` | Customer offer comparison page |
| `apps/portal/templates/portal/offer_select_confirm.html` | Selection confirmation |
| `apps/provider_portal/templates/provider_portal/available_orders.html` | Caregiver order listing |
| `apps/provider_portal/templates/provider_portal/offer_form.html` | Offer submit/edit form |
| `apps/portal/tests/test_offer_views.py` | Customer portal tests |
| `apps/provider_portal/tests/test_offer_views.py` | Caregiver portal tests |

### 13.2 Modified Files

| File | Change |
|------|--------|
| `apps/orders/models.py` | Add OrderOfferStatus, OrderOffer (remove payment_intent FK) |
| `apps/payments/models.py` | Add nullable order_offer FK to PaymentIntent |
| `apps/portal/views.py` | Add offers_compare_view, offer_select_view |
| `apps/portal/urls.py` | Add offer routes |
| `apps/provider_portal/views.py` | Add available_orders_view, offer_submit/edit/withdraw views |
| `apps/provider_portal/urls.py` | Add offer routes |
| `apps/provider_portal/forms.py` | Add OrderOfferForm |
| `apps/kernel/events/base.py` | Add ORDER_OFFER_* event type constants |
| `apps/payments/services/payment_callback_service.py` | Wire payment success → confirm_payment |
| `apps/orders/services/status_machine.py` | Wire order cancellation → cancel_all_for_order |
| `apps/commission/models/deadline.py` | Add nullable order_offer FK |
| `apps/commission/services/deadline_service.py` | Add create_for_offer(), routing in expire_due() |

### 13.3 Files NOT Modified

| File | Reason |
|------|--------|
| `apps/booking/models.py` | No changes to SupplierAssignment |
| `apps/booking/services/assignment_service.py` | Called unchanged at payment time |
| `apps/commission/services/snapshot_service.py` | Called unchanged via AssignmentService |
| `apps/execution/services/session_service.py` | No changes needed |

---

## 14. Ordered Implementation Plan

### Phase 1: Model + Migration

1. Add `OrderOfferStatus` and `OrderOffer` to `apps/orders/models.py`
2. Create migration `0008_orderoffer.py`
3. Add model tests (constraints, defaults, indexes)

### Phase 2: Core Service

4. Create `apps/orders/services/offer_service.py`
5. Implement `submit_offer()` — eligibility check, upsert, event
6. Implement `edit_offer()` — field-whitelisted update
7. Implement `withdraw_offer()` — status transition
8. Implement `select_offer()` — order lock, offer lock, status transition
9. Implement `confirm_payment()` — status transition, AssignmentService.assign()
10. Implement `expire_hold()` — status transition
11. Implement `cancel_all_for_order()` — bulk status transition
12. Implement `list_offers_for_order()`, `list_offers_for_supplier()`
13. Add service tests (all methods, all error paths)

### Phase 3: Concurrency

14. Add lock ordering tests (Order then OrderOffer)
15. Add concurrent selection tests (TransactionTestCase + threading)
16. Add concurrent submission tests (IntegrityError handling)

### Phase 4: Event Wiring

17. Add event type constants to `apps/kernel/events/base.py`
18. Register handlers in `apps/orders/apps.py` (OrdersConfig.ready)
19. Wire payment success → confirm_payment in payment_callback_service.py
20. Wire order cancellation → cancel_all_for_order in status_machine.py

### Phase 5: Caregiver Portal

21. Create `OrderDiscoveryService` (NEW orders visible to caregiver)
22. Add available_orders_view, offer_submit_view, offer_edit_view, offer_withdraw_view
23. Add URL patterns
24. Add templates
25. Add form classes
26. Add view tests

### Phase 6: Customer Portal

27. Add offers_compare_view, offer_select_view
28. Add URL patterns
29. Add templates
30. Add view tests

### Phase 7: Integration

31. Add end-to-end integration tests (full flow)
32. Run full 1632-test suite (zero regressions)
33. Run existing 18-step E2E workflow (still passes)
