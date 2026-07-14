# State Machines

## Reward Lifecycle
Draft -> Pending -> Qualified -> Approved -> Locked -> Earned -> Payable -> Paid

Alternative terminal states:
- Expired
- Cancelled
- Reversed

## Referral Lifecycle
Pending -> Accepted -> Locked
Pending -> Rejected
Pending -> Expired
Accepted -> Invalidated
Locked -> Invalidated only by compliance escalation.

## Campaign Lifecycle
Draft -> Scheduled -> Active -> Paused -> Active -> Expired -> Archived
Draft -> Cancelled
Active -> Cancelled only by authorized operator with audit reason.

## Commission Adjustment Lifecycle
Proposed -> Applied -> Locked -> Settled
Applied -> Reversed if triggering order/payment is reversed.
