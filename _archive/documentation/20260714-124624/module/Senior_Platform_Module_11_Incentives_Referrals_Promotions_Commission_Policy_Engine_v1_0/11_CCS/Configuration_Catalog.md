# CCS Configuration Catalog

## Global Switches
- incentives.enabled
- referrals.enabled
- promotions.enabled
- commission_policy.enabled
- fraud_checks.enabled
- settlement_deferral.enabled

## Campaign Limits
- max_active_campaigns_per_tenant
- max_campaign_budget
- max_daily_reward_amount
- max_monthly_reward_amount
- max_reward_per_actor
- max_referrals_per_actor
- max_rewards_per_source_entity

## Evaluation Settings
- default_conflict_resolution_mode
- allow_reward_stacking
- require_manual_approval_above_amount
- default_reward_expiration_days
- default_referral_expiration_days
- settlement_waiting_period_hours

## Fraud Settings
- block_self_referral
- duplicate_device_threshold
- duplicate_bank_account_action
- vpn_detection_action
- circular_referral_action
- fake_order_signal_threshold

## Audit Settings
- retain_evaluation_inputs
- retain_input_snapshot_hash
- require_policy_change_reason
- require_campaign_publish_approval
