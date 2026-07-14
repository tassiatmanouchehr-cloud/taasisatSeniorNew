# 37 — Commercial Lifecycle and Offer Architecture

## Purpose

The financial lifecycle begins after commercial acceptance, but the accepted offer must be preserved as the source of the contract price.

## Lifecycle

```text
Request / Order Intent
→ Matching
→ Multiple Provider / Organization Offers
→ Customer Accepts One Offer
→ Reservation Created
→ Payment Window Started
→ Payment Successful
→ Commercial Contract Created
→ Contract Price Locked
→ Execution
→ Financial Documents
→ Settlement
```

## Offer Rules

- Multiple independent providers, organization providers, and organizations may submit different offers.
- Customer may accept one offer.
- Accepted offer becomes a reservation.
- Contract is created only after payment completes.
- Contract price is locked forever.
- Changes require Financial Documents, never direct editing.

## Offer Expiration

Offer remains valid while the order is valid unless:

```text
order expires
offer expires
customer accepts another offer
reservation expires
provider withdraws offer, if policy allows
platform invalidates offer
```

## Reservation Failure

If customer accepts an offer but does not pay within the configured payment window:

```text
ReservationExpired
→ Return to previous modules
→ Matching may reopen
→ Archived offers may be reactivated
```

## Archived Offers

Unaccepted offers are not deleted after an accepted offer is selected.

They become archived / inactive.

If reservation fails, platform may reuse or reactivate them according to policy.

```text
Offer A: Accepted → Reservation Failed
Offer B: Archived → Eligible for Reactivation
Offer C: Archived → Eligible for Reactivation
```

## No Counter Offer in Current Scope

The current reference implementation reference implementation does not support negotiation or counter-offers.

Framework should reserve space for future:

```text
counter_offer
negotiated_offer
aI_suggested_offer
operator_adjusted_offer
```

but these are not active in v1.1.
