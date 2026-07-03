# Test Scenarios

## Referral Tests
- valid referral creates accepted relationship
- expired referral is rejected
- self-referral is blocked
- cross-tenant referral is blocked unless policy allows
- manual referral override requires audit reason

## Reward Tests
- signup reward remains pending until eligibility satisfied
- inviter reward qualifies after invitee qualifying order
- reward does not become payable if dispute is open
- reward reverses after refund
- reward expires after configured period

## Commission Tests
- first three orders receive reduced commission if policy says so
- fourth order receives normal commission
- policy version change does not affect previous order
- overlapping campaigns resolve by configured priority

## Fraud Tests
- duplicate bank account creates hold
- circular referral triggers review
- fake order signal blocks payout

## Multi-Tenant Tests
- tenant A cannot view tenant B campaigns
- tenant A policy cannot apply to tenant B actor
