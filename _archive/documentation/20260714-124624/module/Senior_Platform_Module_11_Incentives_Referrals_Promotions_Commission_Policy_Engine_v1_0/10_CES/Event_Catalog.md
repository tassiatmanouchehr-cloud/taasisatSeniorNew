# CES Event Catalog

## Emitted Events
- incentive.campaign.created
- incentive.campaign.published
- incentive.campaign.activated
- incentive.campaign.paused
- incentive.campaign.expired
- incentive.policy.published
- incentive.referral.registered
- incentive.referral.accepted
- incentive.referral.locked
- incentive.referral.invalidated
- incentive.evaluation.completed
- incentive.reward.created
- incentive.reward.qualified
- incentive.reward.approved
- incentive.reward.earned
- incentive.reward.payable
- incentive.reward.paid
- incentive.reward.expired
- incentive.reward.cancelled
- incentive.reward.reversed
- incentive.promotion.applied
- incentive.promotion.removed
- incentive.commission_adjustment.applied
- incentive.commission_adjustment.reversed
- incentive.fraud.hold_created
- incentive.fraud.review_required

## Consumed Events
- identity.actor.registered
- identity.actor.verified
- request.created
- booking.confirmed
- service.completed
- finance.payment.settled
- finance.refund.completed
- finance.ledger.posted
- trust.dispute.opened
- trust.dispute.resolved
- geospatial.location.validated
- notification.delivery.completed

## Event Requirements
All events require tenant_id, correlation_id, causation_id, occurred_at, actor_context, policy_version when applicable, and idempotency_key.
