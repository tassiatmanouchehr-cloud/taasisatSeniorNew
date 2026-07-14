# Reward Lifecycle Specification

## Reward Types
- cash equivalent
- wallet credit
- commission discount
- service discount
- cashback
- coupon
- loyalty points
- subscription credit
- feature entitlement
- rank boost
- badge
- gift
- mixed reward

## Financial Reward Principles
Financial rewards must not directly mutate balances. They become ledger instructions only after settlement qualification.

## Required Reward Fields
reward_id, tenant_id, campaign_id, policy_id, policy_version, beneficiary_actor_id, source_actor_id, source_entity_type, source_entity_id, amount, currency, reward_type, status, qualification_reason, fraud_status, settlement_status, created_at, updated_at.

## Reversal
Rewards may be reversed if payment is refunded, order is cancelled, fraud is confirmed, dispute is upheld, identity is invalidated, or campaign terms require clawback.
