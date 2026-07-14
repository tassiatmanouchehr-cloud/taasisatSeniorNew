# Core Workflows

## Referral Signup Workflow
1. Invite token/code/link is submitted during registration.
2. Identity module validates actor identity and uniqueness.
3. Module 11 validates campaign availability and referral rules.
4. ReferralRelationship is created as pending or accepted.
5. Fraud gates run asynchronously or synchronously according to CCS.
6. Rewards are created as pending only.
7. Notification events are emitted.

## First Orders Reduced Commission Workflow
1. Booking or order lifecycle event is received.
2. Provider eligibility is evaluated.
3. Active commission policies are resolved.
4. CommissionAdjustment is proposed.
5. Module 05 calculates final commission using contract.
6. Adjustment is locked after payment settlement.

## Inviter Earns from Invitee Orders Workflow
1. Invitee completes qualifying order.
2. Execution, payment and dispute status are verified.
3. Referral relationship is checked.
4. Fraud gates run.
5. Reward moves from pending/qualified to earned.
6. Module 05 receives ledger posting request after payable criteria are met.

## Campaign Deactivation Workflow
Deactivation stops new evaluations but never changes historical rewards unless explicit reversal criteria are triggered.
