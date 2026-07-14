# Offer Marketplace — Implementation Contract

**Epic scope:** Customer creates order → eligible caregivers see it → caregivers submit offers → customer compares → customer selects → 30-min hold → payment → booking finalized

**Source of truth:** Repository at commit `a5dbaf28703142edaa1d770ea8f3c2a45a12640f` (1632 tests passing)

**Out of scope:** PR-C (wallet credit), production PSP integration, escrow/dispute/refund flows, unrelated module redesign

---

## 1. Domain Contract

### 1.1 Core Concepts

| Concept | Definition |
|---------|-----------|
| **OrderOffer** | A caregiver's submitted price, terms, estimated duration, and optional message for a specific order. One active offer per caregiver per order. |
| **Offer Hold** | The 30-minute window after a customer selects an offer, during which the order is reserved for that caregiver and the customer must complete payment. |
| **Selection** | The customer's act of choosing one OrderOffer, which triggers the hold and creates a temporary SupplierAssignment in PROPOSED status. |

### 1.2 Business Rules

| Rule | Source | Current State |
|------|--------|---------------|
| BR-OFFER-01: An approved/open order becomes visible to eligible caregivers | Golden flow step 1-2 | **Missing.** No caregiver-facing order browse. |
| BR-OFFER-02: A caregiver may submit one active offer per order | Golden flow step 3 | **Missing.** No OrderOffer model. |
| BR-OFFER-03: Offer contains price (IRR), terms (text), estimated duration (minutes), optional message | Golden flow step 3 | **Missing.** No model. |
| BR-OFFER-04: Caregiver may edit or withdraw offer until customer selects it | Golden flow step 4 | **Missing.** No model or service. |
| BR-OFFER-05: Customer may compare all active offers for their order | Golden flow step 5 | **Missing.** No view or service. |
| BR-OFFER-06: Customer selects exactly one offer | Golden flow step 6 | **Missing.** No selection mechanism. |
| BR-OFFER-07: Selected offer held for 30 minutes | Golden flow step 7 | **Partially exists.** PaymentDeadlineService has 30-min TTL but is gated off. |
| BR-OFFER-08: Failed payment does NOT immediately expire the hold | Golden flow step 8 | **Exists.** FAILED is terminal (transitions.py:14), no cascade to deadline. |
| BR-OFFER-09: Customer may retry payment while hold is active | Golden flow step 9 | **Partially exists.** PaymentIntent creation works, but no "retry" UI for the same order. |
| BR-OFFER-10: Hold expiry → selection expires → assignment released → order available | Golden flow step 10 | **Exists but gated.** PaymentDeadline expiry → AssignmentService.expire() → remove_supplier() → Order.status=NEW. Gate: `commission.payment_deadline.activation_enabled=False`. |
| BR-OFFER-11: Payment success finalizes booking, prevents competing offers | Golden flow step 11 | **Partially exists.** PaymentCallbackService triggers settlement on SUCCEEDED. But no mechanism to close the offer window. |

### 1.3 Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-01 | An order in status `NEW` or `WAITING_SERVICE` may have zero or more open offers | Application layer |
| INV-02 | A caregiver may have at most one offer with status `OPEN` or `SUBMITTED` per order | DB constraint (partial unique index) |
| INV-03 | When a customer selects an offer, `Order.assigned_supplier` is set to that offer's supplier within the same transaction | `select_for_update()` on Order |
| INV-04 | During the hold window, `Order.status = WAITING_SERVICE` and `Order.assigned_supplier = selected supplier` | Set by selection, cleared by expiry |
| INV-05 | Only the order's own customer may select an offer | `ownership_authorized_by` pattern |
| INV-06 | Only the offer's own caregiver may edit/withdraw the offer | `resolve_supplier_for_user()` pattern (same as provider_actions.py) |
| INV-07 | Hold expiry sets `Order.status = NEW`, clears `assigned_supplier`, marks offer `EXPIRED` | PaymentDeadline expiry cascade |
| INV-08 | Payment success marks the hold `COMPLETED`, preventing expiry cascade | `PaymentDeadlineService.mark_completed()` |
| INV-09 | After payment success, all non-selected open offers for the order are marked `SUPERSEDED` | Application layer in selection finalization |
| INV-10 | Two concurrent customer selections on the same order serialize via `select_for_update()` — second attempt fails | DB row lock |

---

## 2. State Machines

### 2.1 OrderOffer Status Machine

```
                    ┌──────────────┐
                    │    (none)    │
                    └──────┬───────┘
                           │ caregiver submits
                           ▼
                    ┌──────────────┐
            ┌──────│    OPEN      │◄──────────────┐
            │      └──────┬───────┘               │
            │             │ caregiver edits        │
            │             ▼                        │
            │      ┌──────────────┐               │
            │      │   EDITED     │───────────────┘
            │      └──────┬───────┘ (can still edit/withdraw)
            │             │ customer views
            │             ▼
            │      ┌──────────────┐
            │      │  SUBMITTED   │◄──────────────┐
            │      └──────┬───────┘               │
            │             │ customer selects      │
            │             ▼                        │
            │      ┌──────────────┐               │
            │      │   SELECTED   │               │
            │      └──────┬───────┘               │
            │             │                        │
            │    ┌────────┴────────┐              │
            │    │                 │              │
            │    ▼                 ▼              │
            │ ┌──────────┐  ┌──────────┐         │
            │ │ PAYMENT_ │  │  HOLD_   │         │
            │ │ SUCCEEDED│  │ EXPIRED  │         │
            │ └──────────┘  └──────────┘         │
            │                                    │
            │ caregiver withdraws                │
            ▼                                    │
     ┌──────────────┐                            │
     │  WITHDRAWN   │                            │
     └──────────────┘                            │
                                                 │
     ┌──────────────┐    (other offer selected)   │
     │ SUPERSEDED   │◄───────────────────────────┘
     └──────────────┘
```

**Transition Table:**

| From | To | Trigger | Guard |
|------|----|---------|-------|
| — | OPEN | `OfferService.submit_offer()` | Caregiver owns supplier, order in NEW/WAITING_SERVICE, no existing OPEN/SUBMITTED offer for this supplier+order |
| OPEN | OPEN | `OfferService.edit_offer()` | Same caregiver, offer not yet SELECTED |
| OPEN | WITHDRAWN | `OfferService.withdraw_offer()` | Same caregiver, offer not yet SELECTED |
| OPEN/SUBMITTED | SUBMITTED | `OfferService.publish_offers()` (internal) | Order becomes visible to customer |
| SUBMITTED | SELECTED | `OfferSelectionService.select_offer()` | Customer owns order, offer belongs to order, order has no current non-expired assignment |
| SUBMITTED | SUPERSEDED | `OfferSelectionService.select_offer()` (on other offers) | Another offer on the same order was selected |
| SELECTED | PAYMENT_SUCCEEDED | `PaymentCallbackService` on SUCCEEDED | PaymentIntent for this order succeeds |
| SELECTED | HOLD_EXPIRED | `PaymentDeadlineService.expire_due()` cascade | 30-minute TTL expires without payment |
| OPEN | WITHDRAWN | `OfferService.withdraw_offer()` | Same caregiver |
| Any except PAYMENT_SUCCEEDED/WITHDRAWN | WITHDRAWN | `OfferService.withdraw_offer()` | Same caregiver, offer not yet selected |

**Note on EDITED status:** EDITED is visually distinct from OPEN but functionally identical for transitions. It exists for audit trail — the customer can see "updated 2 hours ago." If simplicity is preferred, EDITED can be merged into OPEN with an `edited_at` timestamp.

### 2.2 SupplierAssignment Status Changes (Offer Marketplace Path)

The existing SupplierAssignment state machine is **unchanged**. The offer marketplace uses these existing transitions:

| Step | SupplierAssignment Transition | Existing Code |
|------|------------------------------|---------------|
| Customer selects offer | `assign()` creates assignment with status `PROPOSED` (or `ASSIGNED`/`CONFIRMED` per `_initial_status()`) | `AssignmentService.assign()` — **but see §5 for the override needed** |
| Provider confirms | `PROPOSED → CONFIRMED` | `ProviderAssignmentActionService.confirm()` |
| Provider declines | `PROPOSED → DECLINED` | `ProviderAssignmentActionService.decline()` |
| Hold expires | `PROPOSED → EXPIRED` | `AssignmentService.expire()` via `PaymentDeadlineService.expire_due()` |
| Customer cancels after confirmation | `→ CANCELLED` | `AssignmentService.cancel()` |

**Key design decision:** The golden flow needs the assignment to start in a status that does NOT trigger financial core (no CommissionSnapshot, no PaymentDeadline, no PreServiceInvoice at assignment time). Two options:

- **Option A (recommended):** New method `AssignmentService.hold()` that creates the SupplierAssignment in PROPOSED status WITHOUT calling `_open_financial_core_for_assignment()`. Financial core opens later when payment succeeds.
- **Option B:** Add an `initial_status` parameter to `assign()` and skip `_open_financial_core_for_assignment()` when status is PROPOSED. This modifies an existing method's contract.

Option A is safer — it does not change `assign()`'s existing contract.

### 2.3 Order Status Changes

| Step | Order Status Change | Existing Code |
|------|-------------------|---------------|
| Order created | → NEW | `create_public_order()` (currently → PENDING_OPERATOR_REVIEW; golden flow needs → NEW directly or via operator approval) |
| Customer selects offer | NEW → WAITING_SERVICE | `assign_supplier()` in status_machine.py |
| Hold expires | WAITING_SERVICE → NEW | `remove_supplier()` in status_machine.py |
| Payment succeeds | WAITING_SERVICE (unchanged) | No status change needed — order stays WAITING_SERVICE |
| Provider starts execution | WAITING_SERVICE → IN_PROGRESS | `start_order()` |

**Existing status_machine.py functions used unchanged:** `assign_supplier()`, `remove_supplier()`, `start_order()`, `complete_order()`. All use `select_for_update()`.

---

## 3. Invariants (Formal Specification)

### 3.1 Data Invariants

```
I1: ∀ order ∈ Order, ∀ offer ∈ OrderOffer
    offer.order_id = order.id
    → offer.status ∈ {OPEN, EDITED, SUBMITTED, SELECTED, PAYMENT_SUCCEEDED,
                       HOLD_EXPIRED, WITHDRAWN, SUPERSEDED}

I2: ∀ order ∈ Order, ∀ s ∈ Supplier
    count({o ∈ OrderOffer | o.order_id = order.id ∧ o.supplier_id = s.id
                           ∧ o.status ∈ {OPEN, EDITED, SUBMITTED}})
    ≤ 1
    (at most one active offer per caregiver per order)

I3: ∀ order ∈ Order
    count({o ∈ OrderOffer | o.order_id = order.id ∧ o.status = SELECTED})
    ≤ 1
    (at most one selected offer per order)

I4: ∀ order ∈ Order
    (∃ o ∈ OrderOffer | o.status = SELECTED)
    ↔ (order.assigned_supplier_id ≠ None ∧ order.status = WAITING_SERVICE)
    (selection and assignment are coupled)

I5: ∀ order ∈ Order
    (∀ o ∈ OrderOffer | o.status = PAYMENT_SUCCEEDED)
    → order.status ∈ {WAITING_SERVICE, IN_PROGRESS, COMPLETED}
    (payment success prevents order from returning to NEW)
```

### 3.2 Temporal Invariants

```
T1: ∀ o ∈ OrderOffer | o.status = SELECTED
    ∃ d ∈ PaymentDeadline | d.order_id = o.order_id
    ∧ d.status = PENDING
    ∧ d.deadline_at = o.selected_at + 30 minutes
    (selected offer always has a corresponding deadline)

T2: ∀ d ∈ PaymentDeadline | d.status = PENDING ∧ d.deadline_at < now()
    → d.status = EXPIRED ∧ Order.assigned_supplier = None
    (deadline expiry clears assignment)

T3: ∀ o ∈ OrderOffer | o.status = PAYMENT_SUCCEEDED
    → ∄ d ∈ PaymentDeadline | d.order_id = o.order_id ∧ d.status = PENDING
    (payment success cancels pending deadline)
```

---

## 4. Data Model Proposal

### 4.1 New Model: OrderOffer

```python
class OrderOfferStatus(models.TextChoices):
    OPEN = "open", "Open"
    EDITED = "edited", "Edited"
    SUBMITTED = "submitted", "Submitted"
    SELECTED = "selected", "Selected"
    PAYMENT_SUCCEEDED = "payment_succeeded", "Payment Succeeded"
    HOLD_EXPIRED = "hold_expired", "Hold Expired"
    WITHDRAWN = "withdrawn", "Withdrawn"
    SUPERSEDED = "superseded", "Superseded"


class OrderOffer(models.Model):
    """A caregiver's offer on a customer's order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="order_offers",
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="order_offers",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier", on_delete=models.CASCADE, related_name="order_offers",
    )

    # Offer details
    price_amount = models.DecimalField(max_digits=12, decimal_places=0)  # IRR, no decimals
    currency = models.CharField(max_length=3, default="IRR")
    terms = models.TextField(help_text="Caregiver's terms and conditions for this offer")
    estimated_duration_minutes = models.IntegerField(
        help_text="Estimated service duration in minutes",
    )
    message = models.TextField(blank=True, help_text="Optional message to the customer")

    # Status
    status = models.CharField(
        max_length=20, choices=OrderOfferStatus.choices,
        default=OrderOfferStatus.OPEN, db_index=True,
    )

    # Selection tracking
    selected_at = models.DateTimeField(null=True, blank=True)
    selected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )

    # Payment tracking
    payment_succeeded_at = models.DateTimeField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "orders_order_offer"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "supplier"],
                condition=models.Q(status__in=["open", "edited", "submitted"]),
                name="uq_order_offer_active_per_supplier",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_ooffer_tenant_ord_st"),
            models.Index(fields=["tenant", "supplier", "status"], name="idx_ooffer_tenant_sup_st"),
        ]

    def __str__(self):
        return f"OrderOffer(order={self.order_id}, supplier={self.supplier_id}) [{self.status}]"
```

### 4.2 Why Not Extend MatchCandidate

| MatchCandidate | OrderOffer |
|----------------|------------|
| System-generated by matching engine | Caregiver-submitted |
| Has rank_score, rank_position, score_breakdown | Has price_amount, terms, estimated_duration_minutes |
| lifecycle: GENERATED → RANKED → PRESENTED → SELECTED/REJECTED | lifecycle: OPEN → SUBMITTED → SELECTED → PAYMENT_SUCCEEDED/HOLD_EXPIRED |
| FK: match_round | FK: order (direct) |
| No price, no terms, no message | Core purpose is price/terms |

Extending MatchCandidate would conflate two distinct domain concepts with different ownership (system vs caregiver), different fields, and different lifecycles.

### 4.3 Existing Models Used Unchanged

| Model | File | Used For |
|-------|------|----------|
| `SupplierAssignment` | booking/models.py | PROPOSED = temporary hold, CONFIRMED = finalized |
| `PaymentDeadline` | commission/models/deadline.py | 30-minute TTL, expiry cascade |
| `PaymentIntent` | payments/models.py | Payment collection |
| `Order.assigned_supplier` | orders/models.py | Single source of truth for current assignment |

### 4.4 Database Constraints Summary

```sql
-- Partial unique: one active offer per caregiver per order
CREATE UNIQUE INDEX uq_order_offer_active_per_supplier
    ON orders_order_offer (order_id, supplier_id)
    WHERE status IN ('open', 'edited', 'submitted');

-- Index for caregiver's offer list
CREATE INDEX idx_ooffer_tenant_sup_st
    ON orders_order_offer (tenant_id, supplier_id, status);

-- Index for customer's offer comparison
CREATE INDEX idx_ooffer_tenant_ord_st
    ON orders_order_offer (tenant_id, order_id, status);
```

---

## 5. Service Contracts

### 5.1 New Service: OrderDiscoveryService

**File:** `apps/orders/services/order_discovery_service.py` (new)

```python
class OrderDiscoveryService:
    """Makes open orders visible to eligible caregivers."""

    @classmethod
    def list_available_orders(
        cls,
        *,
        supplier,
        category_id=None,
        city=None,
    ) -> list[Order]:
        """
        Returns orders visible to this caregiver:
        - status = NEW or WAITING_SERVICE
        - service_category matches supplier's capabilities
        - not already assigned to this supplier
        - tenant matches

        Uses select_for_update=False (read-only query).
        """

    @classmethod
    def get_order_detail(
        cls,
        *,
        order_id,
        supplier,
    ) -> Order:
        """
        Returns order detail for a caregiver viewing an available order.
        Ownership check: supplier must be eligible for this order's category.
        """
```

**Reuses unchanged:** `EligibilityService.evaluate()` (matching app) for category/tenant checks.

### 5.2 New Service: OrderOfferService

**File:** `apps/orders/services/order_offer_service.py` (new)

```python
class OrderOfferError(Exception):
    pass


class OrderOfferService:
    """Manages the lifecycle of caregiver-submitted offers."""

    @classmethod
    @transaction.atomic
    def submit_offer(
        cls,
        *,
        order_id,
        supplier,
        price_amount: Decimal,
        terms: str,
        estimated_duration_minutes: int,
        message: str = "",
        actor=None,
    ) -> OrderOffer:
        """
        Caregiver submits a new offer on an order.

        Guards:
        - order.status must be NEW or WAITING_SERVICE
        - supplier must be eligible (tenant match, category match)
        - no existing OPEN/SUBMITTED offer for this supplier+order (DB constraint enforces)
        - price_amount > 0
        - estimated_duration_minutes > 0

        Creates OrderOffer with status OPEN.
        """

    @classmethod
    @transaction.atomic
    def edit_offer(
        cls,
        *,
        offer_id,
        supplier,
        price_amount: Decimal = None,
        terms: str = None,
        estimated_duration_minutes: int = None,
        message: str = None,
        actor=None,
    ) -> OrderOffer:
        """
        Caregiver edits their own offer.

        Guards:
        - offer must belong to supplier (ownership check)
        - offer.status must be OPEN or EDITED (not SELECTED, not WITHDRAWN)

        Updates provided fields, sets status to EDITED.
        """

    @classmethod
    @transaction.atomic
    def withdraw_offer(
        cls,
        *,
        offer_id,
        supplier,
        actor=None,
    ) -> OrderOffer:
        """
        Caregiver withdraws their own offer.

        Guards:
        - offer must belong to supplier
        - offer.status must not be PAYMENT_SUCCEEDED or SUPERSEDED

        Sets status to WITHDRAWN, sets withdrawn_at.
        """

    @classmethod
    def list_offers_for_order(
        cls,
        *,
        order_id,
        user,
    ) -> list[OrderOffer]:
        """
        Customer views all active offers for their order.

        Guards:
        - user must be the order's customer (ownership_authorized_by pattern)

        Returns offers with status in {OPEN, EDITED, SUBMITTED, SELECTED}.
        Annotates with supplier reputation score (read-only).
        """

    @classmethod
    def get_offer_detail(
        cls,
        *,
        offer_id,
        user,
    ) -> OrderOffer:
        """
        Customer views a specific offer's details.
        Ownership check on order.
        """
```

### 5.3 New Service: OfferComparisonService

**File:** `apps/orders/services/offer_comparison_service.py` (new)

```python
class OfferComparisonService:
    """Aggregates and enriches offers for customer comparison."""

    @classmethod
    def compare_offers(
        cls,
        *,
        order_id,
        user,
    ) -> list[OfferViewModel]:
        """
        Returns enriched offer data for the customer's comparison view.

        Each OfferViewModel contains:
        - offer: OrderOffer (price, terms, duration, message)
        - supplier_name: str
        - supplier_rating: Decimal (from reviews, default 0)
        - supplier_completed_jobs: int
        - supplier_verification_level: str
        - is_currently_selected: bool

        Guards:
        - user must be the order's customer

        Sorting: default by price ascending, then by supplier rating descending.
        """
```

**Reuses unchanged:** `ReviewService` (reviews app) for supplier ratings, `ServiceSupplier` fields for verification level.

### 5.4 New Service: OfferSelectionService

**File:** `apps/orders/services/offer_selection_service.py` (new)

```python
class OfferSelectionError(Exception):
    pass


class OfferSelectionService:
    """Handles customer selection of an offer and the 30-minute hold."""

    @classmethod
    @transaction.atomic
    def select_offer(
        cls,
        *,
        offer_id,
        user,
    ) -> OfferSelectionResult:
        """
        Customer selects one offer. This is the critical path.

        Steps (all within one transaction):
        1. Fetch OrderOffer with select_for_update() on the ORDER row
        2. Validate: user is order's customer, offer.status is SUBMITTED, order is NEW
        3. Mark this offer as SELECTED (set selected_at, selected_by)
        4. Mark all other active offers for this order as SUPERSEDED
        5. Call AssignmentService.hold() to create SupplierAssignment in PROPOSED
        6. Call _open_financial_core_for_offer_selection() to create
           CommissionSnapshot + PaymentDeadline + PreServiceInvoice
        7. Return OfferSelectionResult(assignment, deadline, invoice)

        Concurrency:
        - Order.objects.select_for_update().get() is the first statement
        - Two concurrent selections serialize; second fails with OfferSelectionError

        Idempotency:
        - If offer is already SELECTED, return existing result (no-op)
        - If order already has assigned_supplier, raise OfferSelectionError
        """

    @classmethod
    @transaction.atomic
    def finalize_selection(
        cls,
        *,
        order_id,
        payment_succeeded: bool,
    ) -> None:
        """
        Called by PaymentCallbackService after payment resolves.

        If payment_succeeded=True:
        - Mark offer as PAYMENT_SUCCEEDED
        - Call PaymentDeadlineService.mark_completed()
        - Order stays WAITING_SERVICE (provider will confirm)

        If payment_succeeded=False:
        - Do NOT mark offer as failed (customer can retry)
        - Leave hold active (PaymentDeadline still PENDING)

        Guards:
        - Order must have a current assignment in PROPOSED status
        """

    @classmethod
    @transaction.atomic
    def expire_hold(
        cls,
        *,
        order_id,
    ) -> None:
        """
        Called by PaymentDeadlineService.expire_due() cascade.

        Steps:
        1. Find current SupplierAssignment (status=PROPOSED)
        2. Call AssignmentService.expire() → removes supplier, order → NEW
        3. Mark selected offer as HOLD_EXPIRED
        4. Mark any remaining active offers as OPEN (re-open for new selections)

        This is the same cascade as the existing PaymentDeadlineService.expire_due()
        but with the addition of marking the OrderOffer as HOLD_EXPIRED.
        """
```

**Critical design point:** `OfferSelectionService.select_offer()` replaces the role of `AssignmentService.assign()` for the golden flow. It calls `AssignmentService.hold()` (new method) instead of `assign()`, and calls `_open_financial_core_for_offer_selection()` instead of `_open_financial_core_for_assignment()`.

### 5.5 Extension: AssignmentService.hold() (New Method)

```python
@classmethod
@transaction.atomic
def hold(
    cls,
    *,
    order_id,
    supplier,
    assigned_by=None,
    metadata=None,
) -> SupplierAssignment:
    """
    Creates a temporary assignment in PROPOSED status for the 30-minute hold.

    DIFFERS FROM assign():
    - Does NOT call _open_financial_core_for_assignment()
    - Always creates SupplierAssignment with status PROPOSED
    - Does NOT call _mark_candidate_selected()
    - The caller (OfferSelectionService) is responsible for opening financial core

    Uses the same concurrency pattern: Order.objects.select_for_update() first.
    Uses the same permission check: PermissionService.require() with
    BOOKING_ASSIGNMENT_ASSIGN and ownership_authorized_by.
    """
```

### 5.6 Reused Unchanged Services

| Service | File | Usage in Offer Marketplace |
|---------|------|---------------------------|
| `AssignmentService.expire()` | booking/services/assignment_service.py | Hold expiry cascade (via PaymentDeadlineService) |
| `AssignmentService.cancel()` | booking/services/assignment_service.py | Customer cancels after confirmation |
| `ProviderAssignmentActionService.confirm()` | booking/services/provider_actions.py | Provider confirms PROPOSED → CONFIRMED |
| `ProviderAssignmentActionService.decline()` | booking/services/provider_actions.py | Provider declines PROPOSED → DECLINED |
| `PaymentDeadlineService.create_for_order()` | commission/services/deadline_service.py | 30-minute TTL creation |
| `PaymentDeadlineService.expire_due()` | commission/services/deadline_service.py | Hold expiry trigger |
| `PaymentDeadlineService.mark_completed()` | commission/services/deadline_service.py | Payment success cancels deadline |
| `CommissionSnapshotService.create_snapshot_for_order()` | commission/services/snapshot_service.py | Commission freeze at selection time |
| `PreServicePaymentService.create_invoice_and_intent_for_order()` | commission/services/preservice_payment_service.py | Invoice + PaymentIntent creation |
| `PaymentCallbackService.process_callback()` | payments/services/payment_callback_service.py | Payment resolution |
| `status_machine.assign_supplier()` | orders/services/status_machine.py | Order → WAITING_SERVICE |
| `status_machine.remove_supplier()` | orders/services/status_machine.py | Order → NEW (on hold expiry) |
| `EligibilityService.evaluate()` | matching/services/eligibility.py | Caregiver eligibility checks |

---

## 6. Authorization Matrix

| Action | Actor | Permission Check | Pattern |
|--------|-------|-----------------|---------|
| View available orders | Caregiver | `resolve_supplier_for_user(actor)` — ownership check | Same as provider_actions.py |
| Submit offer | Caregiver | `resolve_supplier_for_user(actor)` + tenant/category eligibility | New: ownership + eligibility |
| Edit offer | Caregiver (offer owner) | `offer.supplier_id == resolve_supplier_for_user(actor).id` | Same as provider_actions.py |
| Withdraw offer | Caregiver (offer owner) | Same as edit | Same as provider_actions.py |
| View offers (compare) | Customer (order owner) | `ownership_authorized_by=user` where user is order.customer_profile.user | Same as portal views pattern |
| Select offer | Customer (order owner) | `PermissionService.require(user, BOOKING_ASSIGNMENT_ASSIGN, ownership_authorized_by=user)` | Same as AssignmentService.assign() |
| View offer detail | Customer (order owner) | Same as view offers | Same as portal views pattern |
| Confirm assignment | Caregiver (assignment owner) | `resolve_supplier_for_user(actor)` | Reuse provider_actions.py unchanged |
| Decline assignment | Caregiver (assignment owner) | Same as confirm | Reuse provider_actions.py unchanged |

**New permission key needed:** `ORDER_OFFER_SUBMIT` (for caregiver submit/edit/withdraw). This follows the existing pattern where each protected operation has its own key (e.g., `BOOKING_ASSIGNMENT_ASSIGN`, `COMMISSION_DEADLINE_EXTEND`).

---

## 7. Concurrency Strategy

### 7.1 Row-Level Locking (Existing Pattern)

All mutations to `Order` go through `status_machine.py` which uses `Order.objects.select_for_update().get()` as the first statement. This serializes concurrent mutations.

### 7.2 Concurrent Customer Selection

**Scenario:** Two customers (C1, C2) both try to select offers on the same order simultaneously.

**Resolution:**
```
C1: SELECT ... FROM orders_order WHERE id = X FOR UPDATE    -- acquires lock
C1: order.status = NEW, order.assigned_supplier = None      -- reads NEW
C1: ... validates, sets assigned_supplier = supplier_A      -- writes
C1: COMMIT                                                   -- releases lock

C2: SELECT ... FROM orders_order WHERE id = X FOR UPDATE    -- blocks on lock
C2: (C1 commits)                                            -- acquires lock
C2: order.status = WAITING_SERVICE, order.assigned_supplier = supplier_A
C2: ... sees assigned_supplier is already set                -- REJECTS
C2: raises OfferSelectionError("Order already has an active assignment")
C2: ROLLBACK
```

**Implementation:** `OfferSelectionService.select_offer()` acquires `Order.objects.select_for_update()` as its first statement (same as AssignmentService.assign()). After acquiring the lock, it checks `order.assigned_supplier is None`. If already set, raises `OfferSelectionError`.

### 7.3 Concurrent Offer Submission (Same Caregiver)

**Scenario:** A caregiver double-clicks "Submit Offer" on the browser.

**Resolution:** The partial unique constraint `uq_order_offer_active_per_supplier` on `(order_id, supplier_id) WHERE status IN ('open', 'edited', 'submitted')` causes the second INSERT to fail with `IntegrityError`. The service catches this and raises `OrderOfferError("You already have an active offer on this order.")`.

### 7.4 Concurrent Offer Edit

**Scenario:** Caregiver opens two browser tabs and edits the same offer in both.

**Resolution:** No partial unique constraint conflict (status stays OPEN or EDITED). Last write wins. This is acceptable — both edits are from the same caregiver on their own offer.

### 7.5 Hold Expiry vs. Payment Success Race

**Scenario:** The 30-minute hold expires at the exact moment payment succeeds.

**Resolution:** Both paths use `PaymentDeadline.objects.select_for_update()`:
- `PaymentDeadlineService.expire_due()` acquires lock, checks `deadline.status == PENDING`, sets to EXPIRED
- `PaymentDeadlineService.mark_completed()` acquires lock, checks `deadline.status == PENDING`, sets to COMPLETED

Whichever acquires the lock first wins. The loser sees status != PENDING and becomes a no-op (both methods are idempotent on non-PENDING status).

---

## 8. Failure and Retry Behavior

### 8.1 Payment Failure

| State | Behavior |
|-------|----------|
| PaymentIntent → FAILED | `PaymentCallbackService` records failure. `OfferSelectionService.finalize_selection(payment_succeeded=False)` is called. Hold remains active (PaymentDeadline still PENDING). Customer can retry. |
| Customer retries | New PaymentIntent created for the same order. `PreServicePaymentService.create_invoice_and_intent_for_order()` creates a fresh intent (idempotency key derived from PaymentDeadline, so a new intent is correct). |
| Hold expires during retry | PaymentDeadline expiry cascade fires. Offer marked HOLD_EXPIRED. Assignment expired. Order returns to NEW. |

### 8.2 Payment Success

| State | Behavior |
|-------|----------|
| PaymentIntent → SUCCEEDED | `PaymentCallbackService` triggers settlement. `OfferSelectionService.finalize_selection(payment_succeeded=True)` marks offer PAYMENT_SUCCEEDED, calls `PaymentDeadlineService.mark_completed()`. Order stays WAITING_SERVICE. |
| Provider confirms | `ProviderAssignmentActionService.confirm()` → CONFIRMED. Provider can start execution. |

### 8.3 Hold Expiry

| State | Behavior |
|-------|----------|
| PaymentDeadline expires | `expire_due()` fires. `OfferSelectionService.expire_hold()` marks offer HOLD_EXPIRED, calls `AssignmentService.expire()` → `remove_supplier()` → Order.status = NEW. Remaining active offers are re-opened (status → OPEN). |
| Caregiver sees expiry | Offer status = HOLD_EXPIRED. Caregiver can submit a new offer if order is still NEW. |

### 8.4 Error Scenarios

| Error | Handling |
|-------|----------|
| Submit offer on completed/cancelled order | `OrderOfferError("Order is not accepting offers.")` |
| Submit offer when already have active offer | `IntegrityError` caught → `OrderOfferError("You already have an active offer.")` |
| Select offer when order already assigned | `OfferSelectionError("Order already has an active assignment.")` |
| Select offer on non-NEW order | `OfferSelectionError("Order is not available for selection.")` |
| Withdraw offer that is already SELECTED | `OrderOfferError("Cannot withdraw a selected offer.")` |
| Edit offer that is already SELECTED | `OrderOfferError("Cannot edit a selected offer.")` |
| Concurrent selection (race condition) | `OfferSelectionError("Order already has an active assignment.")` (second transaction) |

---

## 9. Migration Impact

### 9.1 New Migration

```
apps/orders/migrations/XXXX_add_orderoffer.py
```

Creates:
- `orders_order_offer` table
- Partial unique index `uq_order_offer_active_per_supplier`
- Composite indexes for tenant+order+status and tenant+supplier+status

### 9.2 No Modifications to Existing Migrations

- `booking_supplier_assignment` — unchanged (PROPOSED status already exists)
- `orders_order` — unchanged (assigned_supplier FK already exists)
- `commission_payment_deadline` — unchanged
- `payments_paymentintent` — unchanged

### 9.3 Feature Gate Enablement

After the Offer Marketplace is implemented and tested, the following gates must be enabled for the golden flow to work end-to-end:

| Gate | Config Key | Default | Required For |
|------|-----------|---------|-------------|
| Deadline activation | `commission.payment_deadline.activation_enabled` | False | Hold expiry cascade |
| Pre-service payment | `commission.preservice_payment.enabled` | False | Invoice + PaymentIntent creation |
| Escrow production | `commission.escrow_production.enabled` | False | Funded escrow (PR-B, out of scope for this epic) |

**Note:** Escrow production is out of scope for this epic. The Offer Marketplace can function with just deadline activation + preservice payment enabled. Escrow is a separate epic.

### 9.4 Data Migration

None. All new data is additive. No existing rows are modified.

---

## 10. Ordered Implementation Plan

### Phase 1: Foundation (no behavioral changes)

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 1.1 | Create `OrderOffer` model + migration | `apps/orders/models.py`, `apps/orders/migrations/` | Nothing |
| 1.2 | Create `OrderOfferService` (submit, edit, withdraw) | `apps/orders/services/order_offer_service.py` | 1.1 |
| 1.3 | Create `ORDER_OFFER_SUBMIT` permission key | `apps/orders/permission_keys.py` | Nothing |
| 1.4 | Tests for OrderOfferService | `apps/orders/tests/test_order_offer_service.py` | 1.2 |

### Phase 2: Discovery and Comparison

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 2.1 | Create `OrderDiscoveryService` | `apps/orders/services/order_discovery_service.py` | 1.1 |
| 2.2 | Create `OfferComparisonService` | `apps/orders/services/offer_comparison_service.py` | 1.2 |
| 2.3 | Tests for discovery and comparison | `apps/orders/tests/test_order_discovery_service.py`, `test_offer_comparison_service.py` | 2.1, 2.2 |

### Phase 3: Selection and Hold

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 3.1 | Add `AssignmentService.hold()` method | `apps/booking/services/assignment_service.py` | Nothing |
| 3.2 | Create `OfferSelectionService` (select, finalize, expire_hold) | `apps/orders/services/offer_selection_service.py` | 1.2, 3.1 |
| 3.3 | Wire PaymentDeadlineService.expire_due() to call OfferSelectionService.expire_hold() | `apps/commission/services/deadline_service.py` | 3.2 |
| 3.4 | Tests for selection + hold + expiry cascade | `apps/orders/tests/test_offer_selection_service.py` | 3.2, 3.3 |

### Phase 4: UI Layer

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 4.1 | Caregiver portal: "Available Orders" page | `apps/provider_portal/views.py`, templates | 2.1 |
| 4.2 | Caregiver portal: "Submit Offer" form | `apps/provider_portal/views.py`, templates, forms | 1.2 |
| 4.3 | Customer portal: "Compare Offers" page | `apps/portal/views.py`, templates | 2.2 |
| 4.4 | Customer portal: "Select Offer" action | `apps/portal/views.py` | 3.2 |
| 4.5 | URL routing for new views | `apps/provider_portal/urls.py`, `apps/portal/urls.py` | 4.1-4.4 |

### Phase 5: Integration

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 5.1 | Enable `commission.payment_deadline.activation_enabled` for test tenant | Config | 3.3 |
| 5.2 | Enable `commission.preservice_payment.enabled` for test tenant | Config | 3.2 |
| 5.3 | Wire PaymentCallbackService to call OfferSelectionService.finalize_selection() | `apps/payments/services/payment_callback_service.py` | 3.2 |
| 5.4 | End-to-end integration test | `tests/integration/` | 5.1-5.3 |

### Phase 6: Polish

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 6.1 | Events for offer lifecycle (submitted, selected, expired, payment_succeeded) | `apps/orders/services/order_offer_service.py` | 1.2 |
| 6.2 | Audit logging for all offer mutations | `apps/orders/services/order_offer_service.py` | 1.2 |
| 6.3 | Notification wiring (caregiver notified when offer selected, customer notified on new offer) | `apps/notifications/` | 1.2, 3.2 |
| 6.4 | Full test suite run — verify 1632+ tests pass | All | All |

---

## Appendix: Service Reuse Matrix

| Existing Service | Method | Used in Offer Marketplace | Modification |
|------------------|--------|--------------------------|--------------|
| `AssignmentService` | `assign()` | **Not used** (replaced by `hold()`) | None |
| `AssignmentService` | `hold()` | **New method** | Add to existing service |
| `AssignmentService` | `expire()` | Hold expiry cascade | None |
| `AssignmentService` | `cancel()` | Customer cancels after confirmation | None |
| `ProviderAssignmentActionService` | `confirm()` | Provider confirms PROPOSED → CONFIRMED | None |
| `ProviderAssignmentActionService` | `decline()` | Provider declines PROPOSED → DECLINED | None |
| `PaymentDeadlineService` | `create_for_order()` | 30-minute TTL creation | None |
| `PaymentDeadlineService` | `expire_due()` | Hold expiry trigger | Add OfferSelectionService.expire_hold() call |
| `PaymentDeadlineService` | `mark_completed()` | Payment success cancels deadline | None |
| `CommissionSnapshotService` | `create_snapshot_for_order()` | Commission freeze at selection time | None |
| `PreServicePaymentService` | `create_invoice_and_intent_for_order()` | Invoice + PaymentIntent creation | None |
| `PaymentCallbackService` | `process_callback()` | Payment resolution | Add OfferSelectionService.finalize_selection() call |
| `status_machine` | `assign_supplier()` | Order → WAITING_SERVICE | None |
| `status_machine` | `remove_supplier()` | Order → NEW (on hold expiry) | None |
| `EligibilityService` | `evaluate()` | Caregiver eligibility checks | None |

**Total new code:** 1 model, 4 services, 1 method extension, 2 wiring changes to existing services, 4 views, 1 permission key.

**Total existing code modified:** 2 files (deadline_service.py: add expire_hold() call; payment_callback_service.py: add finalize_selection() call).
